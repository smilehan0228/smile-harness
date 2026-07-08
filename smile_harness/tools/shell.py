"""受限 shell 工具 — run_shell + 危险子串黑名单。

危险子串黑名单参考 SPEC §3 M2，拦截高危命令。
"""

import subprocess

from smile_harness.tools.base import ToolResult

BLACKLIST: list[str] = [
    "rm -rf",
    "mkfs",
    "dd if",
    "shutdown",
    "reboot",
    ":(){ :|:& };:",
    "chmod 777",
    "> /dev/sda",
    "DROP TABLE",
    "DROP DATABASE",
    "git push --force",
    "git push -f",
]


def run_shell(command: str, cwd: str | None = None) -> ToolResult:
    """执行 shell 命令，黑名单拦截危险指令，超时 30s。"""
    # 黑名单检查（大小写不敏感）
    lower_cmd = command.lower()
    for pattern in BLACKLIST:
        if pattern.lower() in lower_cmd:
            return ToolResult(
                ok=False,
                error=f"Blocked: command contains dangerous pattern '{pattern}'",
            )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            if output:
                output += "\n"
            output += result.stderr
        if not output.strip():
            output = f"Exit code: {result.returncode}"
        return ToolResult(ok=True, content=output.strip())
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, error="Command timed out after 30s")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))