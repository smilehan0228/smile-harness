"""minicc CLI — smile-harness 命令行入口。

使用 argparse 实现，不依赖 click/typer。
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from smile_harness.config import load_config
from smile_harness.creds.manager import CredentialManager
from smile_harness.llm.mock import MockLLM
from smile_harness.loop.main_loop import AgentLoop, LoopConfig
from smile_harness.tools.dispatcher import Dispatcher

# 默认配置文件名
DEFAULT_CONFIG_FILE = "config.yaml"

# 默认 config.yaml 内容
DEFAULT_CONFIG_YAML = """\
# smile-harness 默认配置
tools:
  read_file: true
  write_file: true
  edit_file: true
  list_dir: true
  run_shell: true

guardrail_rules:
  disabled_danger_rules: []

validators:
  enabled:
    - pytest
    - exitcode

llm:
  provider: deepseek
  model: deepseek-chat
  endpoint: https://api.deepseek.com/v1
  temperature: 0.0

max_iters: 5
"""


def _build_parser() -> argparse.ArgumentParser:
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="minicc",
        description="smile-harness — a minimal Python coding agent harness",
    )
    subparsers = parser.add_subparsers(dest="command")

    # minicc task <description>
    task_parser = subparsers.add_parser("task", help="Run a coding task")
    task_parser.add_argument(
        "description", nargs="+", help="Task description"
    )
    task_parser.add_argument(
        "--config", default=DEFAULT_CONFIG_FILE, help="Config file path"
    )

    # minicc config init
    config_parser = subparsers.add_parser("config", help="Config management")
    config_sub = config_parser.add_subparsers(dest="config_action")
    config_sub.add_parser("init", help="Initialize config.yaml")
    config_sub.add_parser("edit", help="Show config file path")

    # minicc key set/show/clear/list
    key_parser = subparsers.add_parser("key", help="Credential management")
    key_sub = key_parser.add_subparsers(dest="key_action")
    key_set = key_sub.add_parser("set", help="Set a credential")
    key_set.add_argument("key", help="Credential key name")
    key_show = key_sub.add_parser("show", help="Show credential status")
    key_show.add_argument("key", help="Credential key name")
    key_clear = key_sub.add_parser("clear", help="Clear a credential")
    key_clear.add_argument("key", help="Credential key name")
    key_sub.add_parser("list", help="List all credentials")

    return parser


def _run_task(args: argparse.Namespace) -> int:
    """运行 coding 任务。

    Args:
        args: 解析后的命令行参数。

    Returns:
        int: 退出码（0 成功，非 0 失败）。
    """
    task_description = " ".join(args.description)

    # 加载配置（如存在）
    config_path = args.config
    if os.path.exists(config_path):
        try:
            config = load_config(config_path)
            max_iters = config.max_iters
            project_root = "."
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1
    else:
        max_iters = 5
        project_root = "."

    # 使用 MockLLM 脚本驱动（真实 LLM 尚未接入）
    # 脚本：先 list_dir 查看项目，然后 final=true 完成
    script = [
        json.dumps({
            "thought": "Let me check the project structure first.",
            "action": "list_dir",
            "action_input": {"path": "."},
            "final": False,
        }),
        json.dumps({
            "thought": f"Task completed: {task_description}",
            "final": True,
        }),
    ]

    llm = MockLLM(script)
    dispatcher = Dispatcher(project_root)
    loop = AgentLoop(
        llm=llm,
        dispatcher=dispatcher,
        config=LoopConfig(max_iters=max_iters, project_root=project_root),
    )

    result = loop.run(task_description)
    print(f"Status: {result['status']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Message: {result['final_message']}")

    return 0 if result["status"] == "success" else 1


def _run_config_init(args: argparse.Namespace) -> int:
    """生成默认 config.yaml 到当前目录。

    Returns:
        int: 退出码。
    """
    config_path = Path(DEFAULT_CONFIG_FILE)
    if config_path.exists():
        print(f"Config file already exists: {config_path.absolute()}", file=sys.stderr)
        return 1

    config_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
    print(f"Created: {config_path.absolute()}")
    return 0


def _run_config_edit(args: argparse.Namespace) -> int:
    """打印 config.yaml 的绝对路径。

    Returns:
        int: 退出码。
    """
    config_path = Path(DEFAULT_CONFIG_FILE).absolute()
    print(str(config_path))
    return 0


def _run_key_set(args: argparse.Namespace) -> int:
    """设置凭据（隐藏输入）。

    Returns:
        int: 退出码。
    """
    try:
        value = getpass.getpass(f"Enter value for '{args.key}': ")
    except (EOFError, KeyboardInterrupt):
        print("", file=sys.stderr)
        return 1

    if not value:
        print("Error: value cannot be empty", file=sys.stderr)
        return 1

    try:
        mgr = CredentialManager()
        mgr.set(args.key, value)
        print(f"Credential '{args.key}' set.")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def _run_key_show(args: argparse.Namespace) -> int:
    """查看凭据状态（不回显明文）。

    Returns:
        int: 退出码。
    """
    try:
        mgr = CredentialManager()
        status = mgr.show(args.key)
        print(f"Credential '{args.key}': {status}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def _run_key_clear(args: argparse.Namespace) -> int:
    """清除凭据。

    Returns:
        int: 退出码。
    """
    try:
        mgr = CredentialManager()
        deleted = mgr.clear(args.key)
        if deleted:
            print(f"Credential '{args.key}' cleared.")
        else:
            print(f"Credential '{args.key}' not found.")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def _run_key_list(args: argparse.Namespace) -> int:
    """列出所有凭据 key。

    Returns:
        int: 退出码。
    """
    mgr = CredentialManager()
    keys = mgr.list_keys()
    if keys:
        for k in keys:
            print(k)
    else:
        print("No credentials found.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数列表（默认 sys.argv[1:]）。

    Returns:
        int: 退出码。
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "task":
        return _run_task(args)
    elif args.command == "config":
        if args.config_action == "init":
            return _run_config_init(args)
        elif args.config_action == "edit":
            return _run_config_edit(args)
        else:
            parser.print_help()
            return 1
    elif args.command == "key":
        if args.key_action == "set":
            return _run_key_set(args)
        elif args.key_action == "show":
            return _run_key_show(args)
        elif args.key_action == "clear":
            return _run_key_clear(args)
        elif args.key_action == "list":
            return _run_key_list(args)
        else:
            parser.print_help()
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())