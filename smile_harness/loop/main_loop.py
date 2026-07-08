"""T12: 主循环集成 — AgentLoop 串联全部 11 模块。

AgentLoop 是 smile-harness 的运行时核心，把 LLM、工具、护栏、HITL、
校验器、反馈闭环、记忆、配置、解析、凭据等模块串成一个可运行的
ReAct agent 主循环。

流程：
    organize_context → call_llm → parse → guardrail → dispatch|hitl
    → validate → reinject → stop_check，循环直至停机。
"""

from __future__ import annotations

from dataclasses import dataclass

from smile_harness.llm.base import LLM, Decision
from smile_harness.tools.dispatcher import Dispatcher
from smile_harness.tools.base import ToolResult
from smile_harness.guardrails.guardrail import guardrail, GuardrailVerdict
from smile_harness.guardrails.hitl import HITLManager, HITLState
from smile_harness.feedback.validator import ValidatorRegistry, FeedbackResult
from smile_harness.feedback.taxonomy import Taxonomy
from smile_harness.feedback.loop import FeedbackLoop
from smile_harness.loop.decision import parse_decision, DecisionParseError
from smile_harness.memory import store as memory_store, retrieve as memory_retrieve


@dataclass
class LoopConfig:
    """主循环配置。

    Attributes:
        max_iters: 最大迭代轮数，默认 5。
        early_stop_threshold: 连续相同非 PASS 反馈的早停阈值，默认 2。
        project_root: 项目根目录（用于护栏路径越界检查）。
    """

    max_iters: int = 5
    early_stop_threshold: int = 2
    project_root: str = "."


class AgentLoop:
    """主循环 — 串起所有模块的 agent 运行时。

    Args:
        llm: LLM 实例（真实或 mock）。
        dispatcher: 工具分发器。
        validator_registry: 校验器注册表（可选）。
        hitl_manager: HITL 审批管理器（可选，默认新建）。
        config: 循环配置（可选，默认 LoopConfig()）。
        memory_dir: 记忆存储目录（可选）。
    """

    def __init__(
        self,
        llm: LLM,
        dispatcher: Dispatcher,
        validator_registry: ValidatorRegistry | None = None,
        hitl_manager: HITLManager | None = None,
        config: LoopConfig | None = None,
        memory_dir: str | None = None,
    ) -> None:
        self._llm = llm
        self._dispatcher = dispatcher
        self._validator_registry = validator_registry or ValidatorRegistry()
        self._hitl_manager = hitl_manager or HITLManager()
        self._config = config or LoopConfig()
        self._memory_dir = memory_dir

    def run(
        self,
        task: str,
        _auto_approve_hitl: bool = True,
        validate: tuple[str, str] | None = None,
    ) -> dict:
        """运行主循环。

        Args:
            task: 任务描述文本。
            _auto_approve_hitl: 测试模式下自动批准 HITL 请求。
            validate: 可选的 (validator_name, target) 元组，
                每轮 dispatch 后自动运行该校验器。

        Returns:
            {
                "status": "success" | "stopped" | "max_iters" | "blocked",
                "iterations": int,
                "feedback_history": list[FeedbackResult],
                "final_message": str,
            }
        """
        feedback_loop = FeedbackLoop(
            max_iters=self._config.max_iters,
            early_stop_threshold=self._config.early_stop_threshold,
        )
        feedback_history: list[FeedbackResult] = []

        # 构建对话历史（system prompt + 记忆）
        messages = self._build_initial_messages(task)

        for iteration in range(1, self._config.max_iters + 1):
            # 1. call_llm → raw_response
            try:
                raw_response = self._llm.complete(messages, self._build_tools())
            except StopIteration:
                should_stop, reason = feedback_loop.should_stop()
                if should_stop:
                    return {
                        "status": "success" if reason == "pass" else "stopped",
                        "iterations": iteration,
                        "feedback_history": feedback_history,
                        "final_message": f"Stopped: {reason}",
                    }
                break

            # 2. 将 LLM 响应追加到对话历史
            messages.append({"role": "assistant", "content": raw_response})

            # 3. parse_decision(raw_response) → Decision
            try:
                decision = parse_decision(raw_response)
            except DecisionParseError as e:
                fb = FeedbackResult(
                    category=Taxonomy.UNKNOWN,
                    message=f"Parse error: {e}",
                    fix_hint="Check the LLM response format",
                    raw=raw_response,
                )
                feedback_loop.record(fb)
                feedback_history.append(fb)
                messages.append({"role": "user", "content": f"Parse error: {e}. Please fix your JSON format."})
                if feedback_loop.should_stop()[0]:
                    break
                continue

            # 4. if decision.final: break (success)
            if decision.final:
                return {
                    "status": "success",
                    "iterations": iteration,
                    "feedback_history": feedback_history,
                    "final_message": decision.thought,
                }

            # 5. guardrail(action, project_root) → verdict
            if decision.action is None:
                fb = FeedbackResult(
                    category=Taxonomy.UNKNOWN,
                    message="No action in non-final decision",
                    fix_hint="",
                    raw="",
                )
                feedback_loop.record(fb)
                feedback_history.append(fb)
                if feedback_loop.should_stop()[0]:
                    break
                continue

            verdict = guardrail(
                decision.action,
                self._config.project_root,
            )

            # 6. if verdict.tier == "fatal": break (blocked)
            if verdict.tier == "fatal":
                fb = FeedbackResult(
                    category=Taxonomy.UNKNOWN,
                    message=f"Fatal action blocked: {verdict.reason}",
                    fix_hint="",
                    raw=verdict.reason,
                )
                feedback_history.append(fb)
                return {
                    "status": "blocked",
                    "iterations": iteration,
                    "feedback_history": feedback_history,
                    "final_message": verdict.reason,
                }

            # 7. if verdict.tier == "danger":
            if verdict.tier == "danger":
                req = self._hitl_manager.submit(decision.action, verdict)
                if _auto_approve_hitl:
                    self._hitl_manager.approve(req.request_id)
                else:
                    if self._hitl_manager.is_pending(req.request_id):
                        fb = FeedbackResult(
                            category=Taxonomy.UNKNOWN,
                            message=f"HITL pending: {verdict.reason}",
                            fix_hint="Awaiting human approval",
                            raw=verdict.reason,
                        )
                        feedback_history.append(fb)
                        return {
                            "status": "blocked",
                            "iterations": iteration,
                            "feedback_history": feedback_history,
                            "final_message": f"HITL required: {verdict.reason}",
                        }

            # 8. 规范化路径参数（LLM 常输出 /hello.py 表示"项目根目录下的 hello.py"）
            if decision.action.name in ("write_file", "edit_file", "read_file", "list_dir"):
                path = decision.action.args.get("path", "")
                if isinstance(path, str) and path.startswith("/"):
                    # 仅单层路径（如 /hello.py → hello.py）strip 前导 /
                    # 多层路径（如 /tmp/xxx/mod.py）保留原样
                    stripped = path[1:]
                    if "/" not in stripped:
                        decision.action.args["path"] = stripped

            # 9. dispatch(action) → ToolResult
            tool_result = self._dispatcher.dispatch(decision.action)

            # 10. 将工具结果喂回对话历史（关键：让 LLM 知道工具执行结果）
            tool_feedback = f"Tool '{decision.action.name}' result: {tool_result.content or '(empty)'}"
            if not tool_result.ok:
                tool_feedback = f"Tool '{decision.action.name}' ERROR: {tool_result.error}"
            messages.append({"role": "user", "content": tool_feedback})

            # 11. if not ToolResult.ok: record failure & continue
            if not tool_result.ok:
                fb = FeedbackResult(
                    category=Taxonomy.UNKNOWN,
                    message=f"Tool error: {tool_result.error}",
                    fix_hint="",
                    raw=tool_result.error or "",
                )
                feedback_loop.record(fb)
                feedback_history.append(fb)
                should_stop, reason = feedback_loop.should_stop()
                if should_stop:
                    return {
                        "status": "stopped",
                        "iterations": iteration,
                        "feedback_history": feedback_history,
                        "final_message": f"Stopped: {reason}",
                    }
                continue

            # 11. validate (if validator configured) → FeedbackResult
            if validate is not None:
                validator_name, target = validate
                try:
                    fb = self._validator_registry.validate(validator_name, target)
                except KeyError:
                    fb = FeedbackResult(
                        category=Taxonomy.UNKNOWN,
                        message=f"Validator '{validator_name}' not found",
                        fix_hint="",
                        raw="",
                    )
                except Exception as e:
                    fb = FeedbackResult(
                        category=Taxonomy.UNKNOWN,
                        message=f"Validator error: {e}",
                        fix_hint="",
                        raw=str(e),
                    )

                feedback_loop.record(fb)
                feedback_history.append(fb)

                should_stop, reason = feedback_loop.should_stop()
                if should_stop:
                    status = "success" if reason == "pass" else "stopped"
                    return {
                        "status": status,
                        "iterations": iteration,
                        "feedback_history": feedback_history,
                        "final_message": fb.message,
                    }

        return {
            "status": "max_iters",
            "iterations": iteration,
            "feedback_history": feedback_history,
            "final_message": "Max iterations reached",
        }

    # ── private helpers ──────────────────────────────────────────────

    def _build_initial_messages(self, task: str) -> list[dict]:
        """构建初始 messages 列表（system prompt + 记忆）。"""
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    f"You are a coding agent. Complete the following task:\n\n"
                    f"{task}\n\n"
                    f"Respond in strict JSON format. If you need to use a tool, respond with:\n"
                    f'{{"thought": "...", "action": "<tool_name>", "action_input": {{...}}, "final": false}}\n\n'
                    f"When the task is complete, respond with:\n"
                    f'{{"thought": "your final answer message", "final": true}}\n\n'
                    f"IMPORTANT: 'final' must be a boolean (true/false), never a string."
                ),
            },
        ]

        # 注入记忆
        if self._memory_dir:
            try:
                entries = memory_retrieve.retrieve(self._memory_dir, task, n=5)
                if entries:
                    memory_text = "Relevant memories:\n"
                    for e in entries:
                        memory_text += f"- [{e.kind}] {e.key}: {e.content}\n"
                    messages.append({"role": "system", "content": memory_text})
            except Exception:
                pass  # 记忆检索失败不应阻塞主循环

        return messages

    def _build_tools(self) -> list[dict]:
        """构建可用工具描述列表（OpenAI function-calling 格式）。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file from the project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to read"}
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to write"},
                            "content": {"type": "string", "description": "Content to write"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edit a file by replacing old_str with new_str.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to edit"},
                            "old_str": {"type": "string", "description": "Text to replace"},
                            "new_str": {"type": "string", "description": "Replacement text"},
                        },
                        "required": ["path", "old_str", "new_str"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "List directory contents.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path to list"}
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_shell",
                    "description": "Run a shell command.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to run"},
                            "cwd": {"type": "string", "description": "Working directory (optional)"},
                        },
                        "required": ["command"],
                    },
                },
            },
        ]