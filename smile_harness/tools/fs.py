"""文件系统工具 — read_file / write_file / edit_file / list_dir。"""

import os

from smile_harness.tools.base import ToolResult


def read_file(path: str) -> ToolResult:
    """读取文件内容。文件不存在时返回 ok=False。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult(ok=True, content=content)
    except FileNotFoundError:
        return ToolResult(ok=False, error=f"File not found: {path}")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def write_file(path: str, content: str) -> ToolResult:
    """写入文件。文件已存在时返回 ok=False (HITL)。"""
    if os.path.exists(path):
        return ToolResult(
            ok=False, error=f"HITL_REQUIRED: file already exists: {path}"
        )
    try:
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(ok=True, content=f"Written: {path}")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def edit_file(path: str, old_str: str, new_str: str) -> ToolResult:
    """在文件中搜索 old_str 并替换为 new_str（仅替换首次出现）。"""
    if not os.path.exists(path):
        return ToolResult(ok=False, error=f"File not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old_str not in content:
            return ToolResult(
                ok=False, error=f"old_str not found in file: {path}"
            )
        count = content.count(old_str)
        if count > 1:
            return ToolResult(
                ok=False,
                error=f"old_str found {count} times, expected exactly once",
            )
        new_content = content.replace(old_str, new_str, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return ToolResult(ok=True, content=f"Edited: {path}")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def list_dir(path: str) -> ToolResult:
    """列出目录内容，返回排序后的条目列表（每行一个）。"""
    try:
        entries = os.listdir(path)
        return ToolResult(ok=True, content="\n".join(sorted(entries)))
    except FileNotFoundError:
        return ToolResult(ok=False, error=f"Directory not found: {path}")
    except NotADirectoryError:
        return ToolResult(ok=False, error=f"Not a directory: {path}")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))