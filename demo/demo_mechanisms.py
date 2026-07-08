"""Smile-harness 机制演示脚本。

运行: python demo/demo_mechanisms.py

三项演示（对应 SPEC A.6）：
  ① 护栏拦截危险动作 — guardrail 拦截 rm -rf /，返回 status="blocked"
  ② 反馈闭环改变行为 — 第一轮产生语法错误反馈，第二轮收到反馈后行为改变
  ③ 修复到全绿 — 多轮自纠，最终 pytest 反馈为 PASS
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# 确保项目根在 sys.path 中，支持直接运行和从项目根运行
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from smile_harness.llm.mock import MockLLM
from smile_harness.tools.dispatcher import Dispatcher
from smile_harness.loop.main_loop import AgentLoop, LoopConfig
from smile_harness.feedback.validator import (
    ValidatorRegistry,
    Validator,
    FeedbackResult,
)
from smile_harness.feedback.taxonomy import Taxonomy
from smile_harness.feedback.pytest_val import PytestValidator


# ── helpers ────────────────────────────────────────────────────────────────


def _make_script(*frames: dict) -> list[str]:
    """将 dict 帧列表转为 JSON 字符串列表（MockLLM 脚本）。"""
    return [json.dumps(f) for f in frames]


# ── 演示① 护栏拦截 ─────────────────────────────────────────────────────────


def demo_guardrail_blocking() -> None:
    """演示①：护栏拦截 fatal action（rm -rf /）"""
    print("=" * 60)
    print("演示①：护栏拦截危险动作")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        script = _make_script(
            {
                "thought": "delete everything",
                "action": "run_shell",
                "action_input": {"command": "rm -rf /"},
                "final": False,
            }
        )
        llm = MockLLM(script)
        dispatcher = Dispatcher(tmp_dir)
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            config=LoopConfig(project_root=tmp_dir),
        )

        result = loop.run("do something dangerous")

        assert result["status"] == "blocked", (
            f"Expected status='blocked', got '{result['status']}'"
        )
        assert "rm -rf" in result["final_message"].lower(), (
            f"Expected 'rm -rf' in final_message, got '{result['final_message']}'"
        )
        print(f"   状态: {result['status']}")
        print(f"   原因: {result['final_message']}")

    print("[PASS] 演示①通过：护栏成功拦截 rm -rf /")
    print()


# ── 演示② 反馈闭环 ─────────────────────────────────────────────────────────


def demo_feedback_changes_behavior() -> None:
    """演示②：失败反馈改变下一步行为"""
    print("=" * 60)
    print("演示②：反馈闭环")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        mod_path = Path(tmp_dir) / "mod.py"

        # 自定义 validator：检查文件是否有语法错误
        class SyntaxCheckValidator(Validator):
            def validate(self, target: str) -> FeedbackResult:
                import ast
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

        # 帧1：写一个有语法错误的 mod.py（缺少冒号）
        # 帧2：收到反馈后改为读文件（行为改变，验证反馈已注入）
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
            {
                "thought": "let me check what I wrote",
                "action": "read_file",
                "action_input": {"path": str(mod_path)},
                "final": False,
            },
        )

        llm = MockLLM(script)
        dispatcher = Dispatcher(tmp_dir)
        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            validator_registry=registry,
            config=LoopConfig(project_root=tmp_dir),
        )

        result = loop.run("write a module", validate=("syntax", str(mod_path)))

        # 第二轮执行了，说明反馈已注入到 context
        assert result["iterations"] >= 2, (
            f"Expected >=2 iterations, got {result['iterations']}"
        )
        assert len(result["feedback_history"]) >= 1, (
            f"Expected >=1 feedback entries, got {len(result['feedback_history'])}"
        )
        print(f"   迭代数: {result['iterations']}")
        print(f"   反馈数: {len(result['feedback_history'])}")
        for i, fb in enumerate(result["feedback_history"]):
            print(f"   反馈[{i}]: {fb.category.value} — {fb.message}")

    print("[PASS] 演示②通过：反馈被注入到下一轮 context")
    print()


# ── 演示③ 修复到全绿 ───────────────────────────────────────────────────────


def demo_fix_to_green() -> None:
    """演示③：修复到全绿 — 多轮自纠，最终 pytest PASS"""
    print("=" * 60)
    print("演示③：修复到全绿")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 复制 test_buggy.py 到临时目录（测试文件已存在）
        broken_module_dir = PROJECT_ROOT / "demo" / "broken_module"
        test_buggy_src = broken_module_dir / "test_buggy.py"
        test_buggy_dst = tmp_path / "test_buggy.py"
        shutil.copy2(str(test_buggy_src), str(test_buggy_dst))

        buggy_path = tmp_path / "buggy.py"

        # 帧1：写 buggy.py（有语法错误 — 缺少冒号）
        # 帧2：跑 pytest 得到失败反馈
        # 帧3：edit_file 修复语法错误（加冒号）
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
            {
                "thought": "run the tests to check",
                "action": "run_shell",
                "action_input": {
                    "command": f"python -m pytest {test_buggy_dst} -q"
                },
                "final": False,
            },
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
        dispatcher = Dispatcher(tmp_dir)

        registry = ValidatorRegistry()
        registry.register("pytest", PytestValidator())

        loop = AgentLoop(
            llm=llm,
            dispatcher=dispatcher,
            validator_registry=registry,
            config=LoopConfig(
                max_iters=5,
                early_stop_threshold=3,
                project_root=tmp_dir,
            ),
        )

        result = loop.run(
            "fix the buggy module", validate=("pytest", str(test_buggy_dst))
        )

        assert result["status"] == "success", (
            f"Expected status='success', got '{result['status']}'"
        )
        assert result["iterations"] == 3, (
            f"Expected 3 iterations, got {result['iterations']}"
        )
        assert result["feedback_history"][-1].category == Taxonomy.PASS, (
            f"Expected final feedback PASS, got {result['feedback_history'][-1].category}"
        )

        # 验证修复确实写入了文件
        fixed_content = buggy_path.read_text()
        assert "def add(a, b):" in fixed_content, "Fix not applied to file!"

        print(f"   状态: {result['status']}")
        print(f"   迭代数: {result['iterations']}")
        for i, fb in enumerate(result["feedback_history"]):
            print(f"   反馈[{i}]: {fb.category.value} — {fb.message}")
        print(f"   修复后的 buggy.py:\n{fixed_content}")

    print("[PASS] 演示③通过：Agent 成功修复语法错误，pytest 转绿")
    print()


# ── main ────────────────────────────────────────────────────────────────────


def main() -> int:
    """运行三项机制演示，任一失败则非零退出。"""
    demo_guardrail_blocking()
    demo_feedback_changes_behavior()
    demo_fix_to_green()
    print("=" * 60)
    print("[ALL PASSED] 全部三项机制演示通过！")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())