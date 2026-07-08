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

        for iteration in range(1, self._config.max_iters + 1):
            # 1. organize_context(task, memory, feedback_history)
            messages = self._organize_context(task, feedback_history)

            # 2. call_llm → raw_response
            try:
                raw_response = self._llm.complete(messages, self._build_tools())
            except StopIteration:
                # LLM 脚本耗尽：检查反馈状态后退出
                should_stop, reason = feedback_loop.should_stop()
                if should_stop:
                    return {
                        "status": "success" if reason == "pass" else "stopped",
                        "iterations": iteration,
                        "feedback_history": feedback_history,
                        "final_message": f"Stopped: {reason}",
                    }
                break

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
                    # 非自动批准模式：检查是否仍为 PENDING
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

            # 8. dispatch(action) → ToolResult
            tool_result = self._dispatcher.dispatch(decision.action)

            # 9. if not ToolResult.ok: record failure & continue
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

            # 10. validate (if validator configured) → FeedbackResult
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

                # 11. feedback_loop.record(result)
                feedback_loop.record(fb)
                feedback_history.append(fb)

                # 12. if feedback_loop.should_stop(): break
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

    def _organize_context(
        self,
        task: str,
        feedback_history: list[FeedbackResult],
    ) -> list[dict]:
        """构建发给 LLM 的 messages 列表。

        包含 system prompt、记忆上下文、以及历史反馈。
        """
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    f"You are a coding agent. Complete the following task:\n\n"
                    f"{task}\n\n"
                    f"Respond in ReAct JSON format with 'thought', 'action', "
                    f"'action_input', and 'final' fields."
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

        # 注入历史反馈
        for fb in feedback_history:
            messages.append({
                "role": "user",
                "content": (
                    f"Previous action feedback: [{fb.category.value}] {fb.message}\n"
                    f"Fix hint: {fb.fix_hint}\n"
                    f"Raw output: {fb.raw}"
                ),
            })

        return messages

    def _build_tools(self) -> list[dict]:
        """构建可用工具描述列表。"""
        return [
            {
                "name": "read_file",
                "description": "Read a file from the project. Args: path (str).",
            },
            {
                "name": "write_file",
                "description": "Write content to a file. Args: path (str), content (str).",
            },
            {
                "name": "edit_file",
                "description": "Edit a file by replacing old_str with new_str. "
                "Args: path (str), old_str (str), new_str (str).",
            },
            {
                "name": "list_dir",
                "description": "List directory contents. Args: path (str).",
            },
            {
                "name": "run_shell",
                "description": "Run a shell command. Args: command (str), cwd (str, optional).",
            },
        ]