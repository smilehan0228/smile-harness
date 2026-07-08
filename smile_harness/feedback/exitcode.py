"""T6: ExitCodeProbe — 运行任意命令，取 exit code 分类"""

import subprocess

from smile_harness.feedback.taxonomy import Taxonomy, classify
from smile_harness.feedback.validator import FeedbackResult, Validator


class ExitCodeProbe(Validator):
    """运行任意命令，取 exit code 分类。

    Args:
        command_template: 命令模板，"{target}" 会被替换为传入的 target。
            默认 "{target}"。
        timeout: 超时秒数，默认 30。
    """

    def __init__(
        self,
        command_template: str = "{target}",
        timeout: int = 30,
    ) -> None:
        self.command_template = command_template
        self.timeout = timeout

    def validate(self, target: str) -> FeedbackResult:
        """运行 target 命令，解析 exit code。

        1. 执行 command_template.format(target=target)
        2. 收集 stdout+stderr 和 exit_code
        3. 调用 classify(raw_output, exit_code) 分类
        4. 返回 FeedbackResult

        Args:
            target: 要执行的命令或文件路径。

        Returns:
            FeedbackResult 包含分类、摘要、修复提示和原始输出。
        """
        command = self.command_template.format(target=target)

        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return FeedbackResult(
                category=Taxonomy.TIMEOUT,
                message=f"Command timed out after {self.timeout}s: {command}",
                fix_hint="Operation took too long — consider increasing timeout or optimizing the command",
                raw=f"Command timed out after {self.timeout}s: {command}",
            )

        raw = proc.stdout + proc.stderr
        category, fix_hint = classify(raw, exit_code=proc.returncode)

        return FeedbackResult(
            category=category,
            message=f"exit code {proc.returncode}: {category.value}",
            fix_hint=fix_hint,
            raw=raw,
        )