"""三级护栏 — guardrail 纯函数，无副作用，无文件 I/O。

对 Action 进行 fatal/danger/safe 三级分类，返回 GuardrailVerdict。
致命规则硬编码不可关闭；危险规则可通过 ``disabled_danger_rules`` 关闭。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal

from smile_harness.llm.base import Action


@dataclass
class GuardrailVerdict:
    """护栏裁决结果。

    Attributes:
        tier: 分类等级 — ``"fatal"`` / ``"danger"`` / ``"safe"``
        blocked: ``True`` = 不可自动执行（致命=拒绝 / 危险=转 HITL）
        reason: 人类可读的裁决理由。
    """

    tier: Literal["fatal", "danger", "safe"]
    blocked: bool
    reason: str


# ── 安全工具名（不检查命令内容即放行） ──────────────────────────────────────
_SAFE_TOOL_NAMES: set[str] = {
    "read_file",
    "list_dir",
}

# ── 受路径约束的工具名（需要检查路径是否在 project_root 内） ──────────────
_PATH_BOUND_TOOL_NAMES: set[str] = {
    "write_file",
    "edit_file",
}

# ── run_shell 安全命令白名单 ────────────────────────────────────────────────
_SAFE_SHELL_COMMANDS: set[str] = {
    "echo", "ls", "pytest", "python", "cat", "grep", "find",
    "mkdir", "touch", "cp", "mv",
}

# ── 致命规则（硬编码，不可关闭） ────────────────────────────────────────────
# 每条规则: (pattern, reason)，pattern 匹配命令字符串（大小写不敏感）
_FATAL_PATTERNS: list[tuple[str, str]] = [
    # rm -rf / 或 rm -rf 无路径参数
    (r'(?:^|\s)rm\s+-rf(?:\s+/|\s*$)', "rm -rf / (or rm -rf without path) is fatal"),
    # mkfs
    (r'\bmkfs\b', "mkfs is fatal"),
    # dd if=... of=... (写磁盘)
    (r'\bdd\s+if=', "dd (disk write) is fatal"),
    # shutdown / reboot / halt
    (r'\b(shutdown|reboot|halt)\b', "system control command is fatal"),
    # fork bomb  :(){ :|:& };:
    (r':\(\)\s*\{', "fork bomb is fatal"),
    # git push --force / git push -f
    (r'\bgit\s+push\b.*(--force|-f)', "git push --force is fatal"),
    # DROP TABLE / DROP DATABASE
    (r'\bDROP\s+(TABLE|DATABASE)\b', "DROP TABLE/DATABASE is fatal"),
]

# ── 危险规则（可通过 disabled_danger_rules 关闭） ───────────────────────────
# 每条规则: (rule_name, pattern, reason)
_DANGER_RULES: list[tuple[str, str, str]] = [
    ("egress", r'\b(curl|wget)\b', "network egress requires HITL"),
    ("git_push", r'\bgit\s+push\b', "git push requires HITL"),
    ("git_commit", r'\bgit\s+commit\b', "git commit requires HITL"),
    ("chmod", r'\bchmod\b', "chmod requires HITL"),
    ("package_install", r'\b(pip|npm)\s+install\b', "package install requires HITL"),
]


def _resolve_path(path: str) -> str:
    """将路径解析为规范化的绝对路径（防 ``..`` 穿越）。

    使用 ``os.path.realpath`` 解析符号链接，消除 ``..`` 和 ``.``。
    """
    return os.path.realpath(os.path.abspath(path))


def _is_path_inside(path: str, root: str) -> bool:
    """检查 *path* 是否在 *root* 目录内（含完全相等）。

    自动处理 LLM 常见的 Unix 风格绝对路径（以 ``/`` 开头），
    将其视为相对于项目根目录的路径。
    """
    # 规范化：移除前导斜杠（LLM 常输出 /hello.py 而非 hello.py）
    normalized = path.lstrip("/").lstrip("\\")
    if normalized != path:
        path = normalized

    resolved_path = _resolve_path(path)
    resolved_root = _resolve_path(root)
    # 确保 root 以分隔符结尾，防止 /root_foo 被误判为 /root 的子目录
    if not resolved_root.endswith(os.sep):
        resolved_root += os.sep
    return resolved_path == resolved_root.rstrip(os.sep) or resolved_path.startswith(resolved_root)


def _extract_command_text(action: Action) -> str | None:
    """从 action 中提取命令文本（用于正则可搜索的内容）。

    对于 ``run_shell`` 返回 ``args["command"]``；对于其他工具返回 ``action.name``。
    """
    if action.name == "run_shell":
        return action.args.get("command", "")
    return action.name


def _check_fatal(extracted_text: str, action: Action, project_root: str) -> GuardrailVerdict | None:
    """检查致命规则，命中则返回 GuardrailVerdict，否则返回 None。"""

    # 0. 写路径越界 — 对 write_file / edit_file 检查 path 参数
    if action.name in _PATH_BOUND_TOOL_NAMES:
        path = action.args.get("path", "")
        if path and not _is_path_inside(path, project_root):
            return GuardrailVerdict(
                tier="fatal",
                blocked=True,
                reason=f"write path outside project root: {path}",
            )

    # 1. 正则匹配致命模式
    if extracted_text:
        for pattern, reason in _FATAL_PATTERNS:
            if re.search(pattern, extracted_text, re.IGNORECASE):
                return GuardrailVerdict(tier="fatal", blocked=True, reason=reason)

    return None


def _check_danger(
    extracted_text: str,
    action: Action,
    disabled_danger_rules: set[str],
    project_root: str,
) -> GuardrailVerdict | None:
    """检查危险规则，命中则返回 GuardrailVerdict，否则返回 None。

    若某条 disabled 规则匹配且无 active 规则匹配，视为安全（放行）。
    若有 active 规则匹配，仍返回 danger。
    """
    disabled_match: tuple[str, str] | None = None  # (rule_name, reason)

    # 0. 空 action name → danger（不可关闭，但按 spec 归类为 danger）
    if action.name == "":
        return GuardrailVerdict(
            tier="danger",
            blocked=True,
            reason="empty action name requires HITL",
        )

    # 1. 正则匹配危险模式 — 先收集所有命中，再决定
    if extracted_text:
        for rule_name, pattern, reason in _DANGER_RULES:
            if not re.search(pattern, extracted_text, re.IGNORECASE):
                continue
            if rule_name in disabled_danger_rules:
                # 记录被关闭的规则命中
                if disabled_match is None:
                    disabled_match = (rule_name, reason)
            else:
                # active 规则命中 → 立即返回 danger
                return GuardrailVerdict(tier="danger", blocked=True, reason=reason)

    # 2. 仅 disabled 规则命中（无 active 命中） → 放行
    if disabled_match is not None:
        return GuardrailVerdict(
            tier="safe",
            blocked=False,
            reason=f"disabled danger rule '{disabled_match[0]}' matched, allowing",
        )

    return None


def _check_safe(action: Action, project_root: str) -> GuardrailVerdict | None:
    """检查安全规则，命中则返回 GuardrailVerdict，否则返回 None。"""

    # 1. 安全工具名（无路径约束）
    if action.name in _SAFE_TOOL_NAMES:
        return GuardrailVerdict(tier="safe", blocked=False, reason=f"{action.name} is safe")

    # 2. 受路径约束的工具 — 路径在项目内则安全
    if action.name in _PATH_BOUND_TOOL_NAMES:
        path = action.args.get("path", "")
        if path and _is_path_inside(path, project_root):
            return GuardrailVerdict(tier="safe", blocked=False, reason=f"{action.name} inside project root")
        # 空路径或无路径 → 由 danger 检查处理

    # 3. run_shell 安全命令
    if action.name == "run_shell":
        command = action.args.get("command", "")
        if command:
            first_word = command.strip().split()[0] if command.strip() else ""
            if first_word in _SAFE_SHELL_COMMANDS:
                return GuardrailVerdict(tier="safe", blocked=False, reason=f"safe shell command: {first_word}")

    return None


def guardrail(
    action: Action,
    project_root: str,
    disabled_danger_rules: set[str] | None = None,
) -> GuardrailVerdict:
    """对 action 执行三级护栏分类。

    Args:
        action: 待检查的 Action。
        project_root: 项目根目录（用于路径越界检查）。
        disabled_danger_rules: 已关闭的危险规则名集合（如 ``{"egress"}``）。

    Returns:
        GuardrailVerdict 裁决结果。
    """
    disabled = disabled_danger_rules or set()
    extracted_text = _extract_command_text(action)

    # 1. 致命规则（不可关闭）
    fatal = _check_fatal(extracted_text, action, project_root)
    if fatal is not None:
        return fatal

    # 2. 危险规则（可关闭）
    danger = _check_danger(extracted_text, action, disabled, project_root)
    if danger is not None:
        return danger

    # 3. 安全规则
    safe = _check_safe(action, project_root)
    if safe is not None:
        return safe

    # 4. 未知 action → danger
    return GuardrailVerdict(
        tier="danger",
        blocked=True,
        reason=f"unknown action '{action.name}' requires HITL",
    )