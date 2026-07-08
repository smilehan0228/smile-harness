"""工具基础类型 — ToolResult。"""

from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """工具执行结果。"""

    ok: bool
    content: str = ""
    error: str | None = None