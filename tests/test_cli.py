"""T14: CLI 测试 — minicc 各个子命令。

测试方式：
  - 通过 unittest.mock.patch 模拟 sys.argv 调用 main()
  - 通过 subprocess 调用 minicc（如已安装）
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

from smile_harness.cli.app import main, DEFAULT_CONFIG_FILE, DEFAULT_CONFIG_YAML


# ── helpers ─────────────────────────────────────────────────────────


def _run_main(*args) -> int:
    """用 mock sys.argv 调用 main()，返回退出码。"""
    with mock.patch.object(sys, "argv", ["minicc"] + list(args)):
        try:
            return main()
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1


# ── test_cli_help ───────────────────────────────────────────────────


def test_cli_help():
    """minicc --help 退出码 0"""
    code = _run_main("--help")
    assert code == 0


def test_cli_help_task_subcommand():
    """minicc task --help 退出码 0"""
    code = _run_main("task", "--help")
    assert code == 0


def test_cli_help_config_subcommand():
    """minicc config --help 退出码 0"""
    code = _run_main("config", "--help")
    assert code == 0


def test_cli_help_key_subcommand():
    """minicc key --help 退出码 0"""
    code = _run_main("key", "--help")
    assert code == 0


def test_cli_no_args_shows_help():
    """minicc 无参数时打印帮助（退出码 0）"""
    code = _run_main()
    assert code == 0


# ── test_key_show_no_key_status ─────────────────────────────────────


def test_key_show_no_key_status(capsys):
    """模拟 key show 未设置的 key → 输出 '未设置'"""
    code = _run_main("key", "show", "nonexistent_key_xyz")
    captured = capsys.readouterr()
    assert "未设置" in captured.out
    assert code == 0


# ── test_config_init_writes_yaml ────────────────────────────────────


def test_config_init_writes_yaml(tmp_path, monkeypatch):
    """config init 生成 config.yaml 并包含必填字段"""
    # 切换到临时目录
    monkeypatch.chdir(tmp_path)

    code = _run_main("config", "init")

    assert code == 0
    config_file = tmp_path / "config.yaml"
    assert config_file.exists()

    # 校验 YAML 内容
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert "tools" in data
    assert "guardrail_rules" in data
    assert "validators" in data
    assert "llm" in data
    assert "max_iters" in data


def test_config_init_already_exists(tmp_path, monkeypatch, capsys):
    """config init 在已存在 config.yaml 时返回错误"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("exists")

    code = _run_main("config", "init")

    assert code == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_config_edit_prints_absolute_path(tmp_path, monkeypatch, capsys):
    """config edit 打印绝对路径"""
    monkeypatch.chdir(tmp_path)

    code = _run_main("config", "edit")

    assert code == 0
    captured = capsys.readouterr()
    output = captured.out.strip()
    assert output == str(Path("config.yaml").absolute())


# ── test_cli_fix_task_mock_green ────────────────────────────────────


def test_cli_fix_task_mock_green(tmp_path, monkeypatch, capsys):
    """用 MockLLM 跑 task 子命令，预期成功"""
    monkeypatch.chdir(tmp_path)

    code = _run_main("task", "fix", "the", "bug")

    assert code == 0
    captured = capsys.readouterr()
    assert "Status: success" in captured.out
    assert "Iterations:" in captured.out


def test_cli_task_with_nonexistent_config(tmp_path, monkeypatch, capsys):
    """task 子命令在 config 不存在时仍能运行（使用默认配置）"""
    monkeypatch.chdir(tmp_path)

    code = _run_main("task", "--config", "nonexistent_config.yaml", "do", "stuff")

    assert code == 0
    captured = capsys.readouterr()
    assert "Status: success" in captured.out


def test_cli_task_with_bad_config(tmp_path, monkeypatch, capsys):
    """task 子命令在 config 格式错误时返回非 0"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bad_config.yaml").write_text("not: [valid: yaml: mapping")

    code = _run_main("task", "--config", "bad_config.yaml", "do", "stuff")

    assert code == 1
    captured = capsys.readouterr()
    assert "Error loading config" in captured.err


# ── test_key_set_and_show ───────────────────────────────────────────


def test_key_set_and_show(monkeypatch, capsys):
    """key set → key show 状态正确"""
    # Mock getpass 避免真实交互
    monkeypatch.setattr("getpass.getpass", lambda prompt: "test-secret-value")

    # 设置凭据
    code = _run_main("key", "set", "test_api_key")
    captured = capsys.readouterr()
    assert code == 0
    assert "set" in captured.out.lower()

    # 查看状态
    code = _run_main("key", "show", "test_api_key")
    captured = capsys.readouterr()
    assert code == 0
    assert "已设置" in captured.out

    # 清理
    from smile_harness.creds.manager import CredentialManager
    mgr = CredentialManager()
    mgr.clear("test_api_key")


def test_key_set_empty_value(monkeypatch, capsys):
    """key set 空值应返回错误"""
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    code = _run_main("key", "set", "test_empty_key")

    assert code == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower()


def test_key_clear_not_found(capsys):
    """key clear 不存在的 key → 提示 not found"""
    code = _run_main("key", "clear", "nonexistent_key_abc123")

    assert code == 0
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()


def test_key_clear_found(monkeypatch, capsys):
    """key set → key clear → 成功清除"""
    monkeypatch.setattr("getpass.getpass", lambda prompt: "test-value")

    _run_main("key", "set", "test_clear_key")
    code = _run_main("key", "clear", "test_clear_key")

    assert code == 0
    captured = capsys.readouterr()
    assert "cleared" in captured.out.lower()


def test_key_list_empty(capsys, monkeypatch):
    """key list 无凭据时提示"""
    code = _run_main("key", "list")

    assert code == 0
    captured = capsys.readouterr()
    # 可能为空输出或 "No credentials found"
    assert "No credentials found" in captured.out or captured.out.strip() == ""


def test_key_list_with_entries(monkeypatch, capsys):
    """key list 有凭据时列出"""
    monkeypatch.setattr("getpass.getpass", lambda prompt: "test-value")

    _run_main("key", "set", "test_list_key")
    code = _run_main("key", "list")

    assert code == 0
    captured = capsys.readouterr()
    assert "test_list_key" in captured.out

    # 清理
    from smile_harness.creds.manager import CredentialManager
    CredentialManager().clear("test_list_key")


def test_key_invalid_name(capsys):
    """key set 无效名称应返回错误"""
    code = _run_main("key", "show", "key with spaces")

    assert code == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err


# ── subprocess 测试（如果 minicc 已安装）───────────────────────────


@pytest.mark.skipif(
    subprocess.run(
        [sys.executable, "-m", "pip", "show", "smile-harness"],
        capture_output=True,
    ).returncode != 0,
    reason="smile-harness not installed (pip install -e . required)",
)
def test_minicc_subprocess_help():
    """通过 subprocess 调用 minicc --help"""
    result = subprocess.run(
        ["minicc", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "minicc" in result.stdout
    assert "task" in result.stdout
    assert "config" in result.stdout
    assert "key" in result.stdout