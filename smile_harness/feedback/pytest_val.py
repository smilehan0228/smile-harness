"""T6: PytestValidator — 运行 pytest 并解析输出"""

import subprocess
import sys

from smile_harness.feedback.taxonomy import Taxonomy, classify
from smile_harness.feedback.validator import FeedbackResult, Validator


class PytestValidator(Validator):
    """运行 pytest 并解析输出，归类为 FeedbackResult。

    Args:
        pytest_args: 传给 pytest 的额外参数列表，默认 ["-q"]。
    """

    def __init__(self, pytest_args: list[str] | None = None) -> None:
        self.pytest_args = pytest_args if pytest_args is not None else ["-q"]

    def validate(self, target: str) -> FeedbackResult:
        """对 target 文件运行 pytest，解析输出。

        1. 执行 pytest target [pytest_args]
        2. 收集 stdout+stderr 和 exit_code
        3. 调用 classify(raw_output, exit_code) 分类
        4. 返回 FeedbackResult

        Args:
            target: 要测试的 Python 文件路径。

        Returns:
            FeedbackResult 包含分类、摘要、修复提示和原始输出。
        """
        cmd = [sys.executable, "-m", "pytest", target] + self.pytest_args

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            return FeedbackResult(
                category=Taxonomy.UNKNOWN,
                message="pytest not found",
                fix_hint="Ensure pytest is installed in the current environment",
                raw="pytest not found",
            )
        except subprocess.TimeoutExpired:
            return FeedbackResult(
                category=Taxonomy.TIMEOUT,
                message="pytest timed out",
                fix_hint="Operation took too long — consider increasing timeout or simplifying tests",
                raw="pytest timed out",
            )

        raw = proc.stdout + proc.stderr
        category, fix_hint = classify(raw, exit_code=proc.returncode)

        return FeedbackResult(
            category=category,
            message=f"pytest on {target}: {category.value}",
            fix_hint=fix_hint,
            raw=raw,
        )