"""工具分发器 — 根据 Action.name 路由到对应工具函数。"""

from smile_harness.llm.base import Action
from smile_harness.tools import fs
from smile_harness.tools import shell
from smile_harness.tools.base import ToolResult


class Dispatcher:
    """工具分发器，将 Action 路由到对应的工具函数。

    Args:
        project_root: 项目根目录（预留，供后续 guardrail 使用）。
    """

    def __init__(self, project_root: str) -> None:
        self._project_root: str = project_root
        self._routes: dict[str, callable] = {
            "read_file": fs.read_file,
            "write_file": fs.write_file,
            "edit_file": fs.edit_file,
            "list_dir": fs.list_dir,
            "run_shell": shell.run_shell,
        }

    def dispatch(self, action: Action) -> ToolResult:
        """根据 action.name 路由到对应工具并执行。

        自动规范化路径参数（移除前导斜杠，LLM 常输出 /hello.py）。

        Args:
            action: 包含 name 和 args 的 Action 对象。

        Returns:
            ToolResult 表示执行结果。
        """
        fn = self._routes.get(action.name)
        if fn is None:
            return ToolResult(
                ok=False, error=f"Unknown action: {action.name}"
            )
        # 规范化路径参数：移除前导斜杠（LLM 常输出 Unix 风格路径）
        args = dict(action.args)
        if "path" in args and isinstance(args["path"], str):
            args["path"] = args["path"].lstrip("/").lstrip("\\") or "."
        try:
            return fn(**args)
        except TypeError as e:
            return ToolResult(ok=False, error=f"Action argument error: {e}")
        except Exception as e:
            return ToolResult(ok=False, error=str(e))