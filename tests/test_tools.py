"""T2 工具模块测试 — 文件读写改列 + 受限 shell + 工具分发。"""

import pytest

from smile_harness.tools.base import ToolResult
from smile_harness.tools import fs
from smile_harness.tools import shell
from smile_harness.tools.dispatcher import Dispatcher
from smile_harness.llm.base import Action


# ── 1. read_nonexistent ──────────────────────────────────────────────

def test_read_nonexistent_returns_not_ok():
    result = fs.read_file("/nonexistent/path/12345_test_file.txt")
    assert result.ok is False
    assert result.error is not None


# ── 2. write → read roundtrip ────────────────────────────────────────

def test_write_then_read_roundtrip(tmp_path):
    path = str(tmp_path / "hello.txt")
    content = "hello world\n"
    w = fs.write_file(path, content)
    assert w.ok is True
    r = fs.read_file(path)
    assert r.ok is True
    assert r.content == content


# ── 3. edit_file ─────────────────────────────────────────────────────

def test_edit_patch_applies(tmp_path):
    path = str(tmp_path / "edit.txt")
    fs.write_file(path, "line1\nline2\nline3\n")
    result = fs.edit_file(path, old_str="line2", new_str="replaced")
    assert result.ok is True
    after = fs.read_file(path)
    assert "replaced" in after.content
    assert "line2\n" not in after.content


# ── 4. shell blacklist ───────────────────────────────────────────────

def test_shell_blacklist_blocks_rm_rf():
    result = shell.run_shell("rm -rf /")
    assert result.ok is False
    assert result.error is not None


# ── 5. shell safe command ────────────────────────────────────────────

def test_shell_allows_safe_command():
    result = shell.run_shell("echo hello")
    assert result.ok is True
    assert "hello" in result.content


# ── 6. list_dir ──────────────────────────────────────────────────────

def test_list_dir_returns_contents(tmp_path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.txt").write_text("")
    result = fs.list_dir(str(tmp_path))
    assert result.ok is True
    assert "a.txt" in result.content
    assert "b.txt" in result.content


# ── 7. write existing file → HITL ────────────────────────────────────

def test_write_existing_file_returns_hitl(tmp_path):
    path = str(tmp_path / "existing.txt")
    fs.write_file(path, "initial")
    result = fs.write_file(path, "new content")
    assert result.ok is False
    assert result.error is not None
    assert "HITL" in result.error


# ── 8. dispatcher routes correctly ───────────────────────────────────

def test_dispatcher_routes_correctly(tmp_path):
    d = Dispatcher(project_root=str(tmp_path))

    # read_file
    r = d.dispatch(Action(name="read_file", args={"path": "/nonexistent/xyz"}))
    assert isinstance(r, ToolResult)
    assert r.ok is False  # nonexistent file

    # write_file
    p = str(tmp_path / "disp.txt")
    r = d.dispatch(Action(name="write_file", args={"path": p, "content": "x"}))
    assert r.ok is True

    # edit_file
    r = d.dispatch(Action(name="edit_file", args={"path": p, "old_str": "x", "new_str": "y"}))
    assert r.ok is True

    # list_dir
    r = d.dispatch(Action(name="list_dir", args={"path": str(tmp_path)}))
    assert r.ok is True
    assert "disp.txt" in r.content

    # run_shell safe
    r = d.dispatch(Action(name="run_shell", args={"command": "echo ok"}))
    assert r.ok is True
    assert "ok" in r.content


# ── 9. dispatcher unknown action ─────────────────────────────────────

def test_dispatcher_unknown_action():
    d = Dispatcher(project_root="/tmp")
    r = d.dispatch(Action(name="fly_to_moon", args={}))
    assert r.ok is False
    assert r.error is not None
    assert "Unknown" in r.error or "unknown" in r.error