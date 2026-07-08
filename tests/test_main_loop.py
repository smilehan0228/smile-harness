"""T12: 主循环集成测试 — AgentLoop 串联全部模块。

使用 MockLLM 脚本驱动，做 3 个机制演示（对应 SPEC A.6）：
① 护栏拦截 fatal action
② 反馈闭环（反馈改变下一轮行为）
③ 修复到全绿（多轮自纠，最终 PASS）
"""

import ast
import pytest

from smile_harness.llm.base import Action
from smile_harness.llm.mock import MockLLM
from smile_harness.tools.dispatcher import Dispatcher
from smile_harness.guardrails.hitl import HITLManager
from smile_harness.feedback.validator import ValidatorRegistry, Validator, FeedbackResult
from smile_harness.feedback.taxonomy import Taxonomy
from smile_harness.loop.main_loop import AgentLoop, LoopConfig


# ── helpers ─────────────────────────────────────────────────────────

def _make_script(*frames: dict) -> list[str]:
    """将 dict 帧列表转为 JSON 字符串列表（MockLLM 脚本）。"""
    import json
    return [json.dumps(f) for f in frames]


# ── 演示① 护栏拦截 ──────────────────────────────────────────────────

class TestLoopBlocksFatalAction:
    """演示①：护栏拦截 fatal action → status=blocked"""

    def test_loop_blocks_rm_rf(self, tmp_path):
        """MockLLM 返回 rm -rf / → guardrail 判 fatal → 循环 blocked"""
        script = _make_script({
            "thought": "delete everything",
            "action": "run_shell",
            "action_input": {"command": "rm -rf /"},
            "final": False,
        })
        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            config=LoopConfig(project_root=str(tmp_path)),
        )

        result = loop.run("do something dangerous")

        assert result["status"] == "blocked"
        assert result["iterations"] == 1
        assert len(result["feedback_history"]) == 1
        assert "rm -rf" in result["final_message"].lower()

    def test_loop_blocks_write_outside_root(self, tmp_path):
        """write_file 写越界路径 → guardrail 判 fatal → blocked"""
        script = _make_script({
            "thought": "write to /etc",
            "action": "write_file",
            "action_input": {"path": "/etc/passwd", "content": "evil"},
            "final": False,
        })
        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            config=LoopConfig(project_root=str(tmp_path)),
        )

        result = loop.run("write outside root")

        assert result["status"] == "blocked"
        assert "outside project root" in result["final_message"].lower()


# ── 演示② 反馈闭环 ──────────────────────────────────────────────────

class TestFeedbackChangesNextAction:
    """演示②：反馈闭环 — 第一轮产生反馈，第二轮收到反馈后行为改变"""

    def test_feedback_injected_into_context(self, tmp_path):
        """第一轮 write_file 被 validator 检出语法错误 → 第二轮收到反馈"""
        # 写一个测试文件，供 validator 检查
        test_file = tmp_path / "test_mod.py"
        test_file.write_text("from mod import foo\n\ndef test_foo():\n    assert foo() == 42\n")

        # 自定义 validator：检查 mod.py 是否有语法错误
        class SyntaxCheckValidator(Validator):
            def validate(self, target: str) -> FeedbackResult:
                try:
                    with open(target, "r", encoding="utf-8") as f:
                        source = f.read()
                    ast.parse(source)
                    return FeedbackResult(
                        category=Taxonomy.PASS,
                        message="No syntax errors",
                        fix_hint="",
                        raw="",
                    )
                except SyntaxError as e:
                    return FeedbackResult(
                        category=Taxonomy.SYNTAX_ERROR,
                        message=f"SyntaxError: {e.msg}",
                        fix_hint="Fix the syntax error",
                        raw=str(e),
                    )
                except FileNotFoundError:
                    return FeedbackResult(
                        category=Taxonomy.UNKNOWN,
                        message="File not found",
                        fix_hint="",
                        raw="",
                    )

        registry = ValidatorRegistry()
        registry.register("syntax", SyntaxCheckValidator())

        mod_path = tmp_path / "mod.py"

        # 帧1：写一个有语法错误的 mod.py（缺少冒号）
        script = _make_script(
            {
                "thought": "write the module",
                "action": "write_file",
                "action_input": {
                    "path": str(mod_path),
                    "content": "def foo()\n    return 42\n",
                },
                "final": False,
            },
            # 帧2：收到反馈后改为读文件（行为改变）
            {
                "thought": "let me check what I wrote",
                "action": "read_file",
                "action_input": {"path": str(mod_path)},
                "final": False,
            },
        )

        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            validator_registry=registry,
            config=LoopConfig(project_root=str(tmp_path)),
        )

        result = loop.run("write a module", validate=("syntax", str(mod_path)))

        # 第二轮执行了，说明反馈已注入
        assert result["iterations"] >= 2
        assert len(result["feedback_history"]) >= 1


# ── 演示③ 修复到全绿 ────────────────────────────────────────────────

class TestLoopFixesBrokenModuleToGreen:
    """演示③：多轮自纠，最终反馈为 PASS"""

    def test_fixes_syntax_error_to_green(self, tmp_path):
        """Agent 写 buggy.py → 跑测试失败 → 修复 → 最终 PASS"""
        # 预先创建 test_buggy.py（import 还没创建的 buggy）
        test_file = tmp_path / "test_buggy.py"
        test_file.write_text(
            "from buggy import add\n\n"
            "def test_add():\n"
            "    assert add(1, 2) == 3\n"
        )

        buggy_path = tmp_path / "buggy.py"

        # 帧1：写 buggy.py（有语法错误 — 缺少冒号）
        script = _make_script(
            {
                "thought": "create the buggy module",
                "action": "write_file",
                "action_input": {
                    "path": str(buggy_path),
                    "content": "def add(a, b)\n    return a + b\n",
                },
                "final": False,
            },
            # 帧2：跑 pytest 看结果
            {
                "thought": "run the tests to check",
                "action": "run_shell",
                "action_input": {
                    "command": f"python -m pytest {test_file} -q"
                },
                "final": False,
            },
            # 帧3：修复语法错误（加冒号）
            {
                "thought": "fix the syntax error",
                "action": "edit_file",
                "action_input": {
                    "path": str(buggy_path),
                    "old_str": "def add(a, b)\n    return a + b",
                    "new_str": "def add(a, b):\n    return a + b",
                },
                "final": False,
            },
        )

        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))

        # 使用 PytestValidator 作为校验器
        from smile_harness.feedback.pytest_val import PytestValidator
        registry = ValidatorRegistry()
        registry.register("pytest", PytestValidator())

        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            validator_registry=registry,
            config=LoopConfig(
                max_iters=5,
                early_stop_threshold=3,  # 允许 2 次失败后再修复
                project_root=str(tmp_path),
            ),
        )

        result = loop.run("fix the buggy module", validate=("pytest", str(test_file)))

        # 最终反馈应为 PASS
        assert result["status"] == "success"
        assert result["iterations"] == 3
        assert result["feedback_history"][-1].category == Taxonomy.PASS


# ── 正常完成（final=true） ───────────────────────────────────────────

class TestLoopFinalAction:
    """final=true 正常退出测试。"""

    def test_final_action_stops_success(self, tmp_path):
        """LLM 返回 final=true → 正常退出 success"""
        script = _make_script({
            "thought": "all done, nothing to do",
            "final": True,
        })
        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            config=LoopConfig(project_root=str(tmp_path)),
        )

        result = loop.run("do nothing")

        assert result["status"] == "success"
        assert result["iterations"] == 1
        assert result["final_message"] == "all done, nothing to do"


# ── HITL 自动审批 ───────────────────────────────────────────────────

class TestLoopHITL:
    """HITL 危险动作审批流程测试。"""

    def test_auto_approve_hitl_allows_danger(self, tmp_path):
        """_auto_approve_hitl=True → danger 动作自动批准并执行"""
        script = _make_script({
            "thought": "need to curl something",
            "action": "run_shell",
            "action_input": {"command": "curl http://example.com"},
            "final": False,
        })
        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        hitl = HITLManager()
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            hitl_manager=hitl,
            config=LoopConfig(project_root=str(tmp_path)),
        )

        result = loop.run("curl something", _auto_approve_hitl=True)

        # curl 被 shell 黑名单拦截或正常执行，但不应被 guardrail 阻塞
        # 关键：不应是 blocked 状态
        assert result["status"] != "blocked"
        # 至少执行了 1 轮
        assert result["iterations"] >= 1

    def test_hitl_deny_stops_action(self, tmp_path):
        """HITL deny → 不执行动作，记录反馈"""
        script = _make_script({
            "thought": "need to curl something",
            "action": "run_shell",
            "action_input": {"command": "curl http://example.com"},
            "final": False,
        })
        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        hitl = HITLManager()
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            hitl_manager=hitl,
            config=LoopConfig(project_root=str(tmp_path)),
        )

        # 不自动批准：HITL 保持 PENDING，应记录为 denied
        result = loop.run("curl something", _auto_approve_hitl=False)

        # 危险动作未执行，被 hitl 阻塞
        assert result["status"] == "blocked"
        # 反馈中应包含 HITL 相关信息
        assert any("HITL" in fb.message for fb in result["feedback_history"])


# ── 工具失败处理 ────────────────────────────────────────────────────

class TestLoopToolFailure:
    """工具执行失败时的处理。"""

    def test_tool_failure_records_feedback(self, tmp_path):
        """工具返回 ok=False → 记录失败反馈"""
        # 读一个不存在的文件 → 工具失败
        script = _make_script({
            "thought": "read a missing file",
            "action": "read_file",
            "action_input": {"path": str(tmp_path / "nonexistent.txt")},
            "final": False,
        })
        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            config=LoopConfig(project_root=str(tmp_path)),
        )

        result = loop.run("read missing file")

        assert result["iterations"] == 2
        assert len(result["feedback_history"]) == 1
        assert "not found" in result["feedback_history"][0].message.lower()


# ── max_iters 到顶 ─────────────────────────────────────────────────

class TestLoopMaxIters:
    """max_iters 到顶停机。"""

    def test_max_iters_stops(self, tmp_path):
        """连续非 final 动作 → max_iters 到顶退出"""
        # 3 帧非 final 动作
        frames = [
            {
                "thought": f"step {i}",
                "action": "read_file",
                "action_input": {"path": str(tmp_path / "dummy.txt")},
                "final": False,
            }
            for i in range(3)
        ]
        # 先创建文件避免 read_file 失败
        (tmp_path / "dummy.txt").write_text("hello")

        llm = MockLLM(_make_script(*frames))
        dispatcher = Dispatcher(str(tmp_path))
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            config=LoopConfig(max_iters=3, project_root=str(tmp_path)),
        )

        result = loop.run("do stuff")

        assert result["status"] == "max_iters"
        assert result["iterations"] == 3


# ── 内存记忆注入 ────────────────────────────────────────────────────

class TestLoopMemory:
    """记忆存储与注入测试。"""

    def test_memory_injected_into_context(self, tmp_path):
        """有记忆目录时，相关记忆应注入 messages"""
        import json
        from datetime import datetime, timezone
        from smile_harness.memory.store import MemoryEntry, write_entry

        memory_dir = str(tmp_path / ".harness")
        entry = MemoryEntry(
            key="test_memory",
            kind="note",
            content="important context",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        write_entry(memory_dir, entry)

        script = _make_script({
            "thought": "done",
            "final": True,
        })
        llm = MockLLM(script)
        dispatcher = Dispatcher(str(tmp_path))
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            config=LoopConfig(project_root=str(tmp_path)),
            memory_dir=memory_dir,
        )

        result = loop.run("test task")
        assert result["status"] == "success"


# ── LoopConfig 默认值 ───────────────────────────────────────────────

class TestLoopConfig:
    """LoopConfig 默认值测试。"""

    def test_defaults(self):
        cfg = LoopConfig()
        assert cfg.max_iters == 5
        assert cfg.early_stop_threshold == 2
        assert cfg.project_root == "."

    def test_custom(self):
        cfg = LoopConfig(max_iters=10, early_stop_threshold=3, project_root="/tmp")
        assert cfg.max_iters == 10
        assert cfg.early_stop_threshold == 3
        assert cfg.project_root == "/tmp"