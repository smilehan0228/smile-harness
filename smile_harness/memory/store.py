"""记忆存储 — MemoryEntry 读写、列出、删除。

文件格式：每个 MemoryEntry 对应 .harness/ 下一个 .md 文件。
文件头部是 YAML-like front matter（key, kind, updated_at），
正文是 content。"""

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone


# ── 数据模型 ─────────────────────────────────────────────────────


@dataclass
class MemoryEntry:
    key: str
    kind: str
    content: str
    updated_at: str  # ISO 8601


# ── 敏感词检测 ───────────────────────────────────────────────────

_CREDENTIAL_PATTERNS = [
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
    re.compile(r"\bapi_key\b", re.IGNORECASE),
    re.compile(r"\bsecret\b", re.IGNORECASE),
]


def _contains_credentials(text: str) -> bool:
    return any(p.search(text) for p in _CREDENTIAL_PATTERNS)


# ── 文件序列化 ───────────────────────────────────────────────────


def _file_path(store_dir: str, key: str) -> str:
    return os.path.join(store_dir, f"{key}.md")


def _serialize(entry: MemoryEntry) -> str:
    return (
        f"---\n"
        f"key: {entry.key}\n"
        f"kind: {entry.kind}\n"
        f"updated_at: {entry.updated_at}\n"
        f"---\n"
        f"{entry.content}\n"
    )


def _deserialize(text: str) -> MemoryEntry | None:
    """从 .md 文本解析 MemoryEntry。损坏文件返回 None。"""
    try:
        m = re.match(
            r"^---\s*\n"
            r"key:\s*(.+?)\s*\n"
            r"kind:\s*(.+?)\s*\n"
            r"updated_at:\s*(.+?)\s*\n"
            r"---\s*\n",
            text,
        )
        if not m:
            return None
        key = m.group(1).strip()
        kind = m.group(2).strip()
        updated_at = m.group(3).strip()
        content = text[m.end() :].rstrip("\n")
        return MemoryEntry(key=key, kind=kind, content=content, updated_at=updated_at)
    except Exception:
        return None


# ── 公开 API ─────────────────────────────────────────────────────


def write_entry(store_dir: str, entry: MemoryEntry) -> None:
    """将 MemoryEntry 写入 .harness/ 目录下的 .md 文件。"""
    # 安全约束：拒绝凭据
    if _contains_credentials(entry.content):
        raise ValueError(
            f"Memory content for key '{entry.key}' contains credential-like patterns "
            f"(password/token/api_key/secret). Refusing to store."
        )
    os.makedirs(store_dir, exist_ok=True)
    path = _file_path(store_dir, entry.key)
    text = _serialize(entry)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_entry(store_dir: str, key: str) -> MemoryEntry | None:
    """读取指定 key 的记忆条目。"""
    path = _file_path(store_dir, key)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return _deserialize(text)
    except Exception:
        return None


def list_entries(store_dir: str) -> list[MemoryEntry]:
    """列出所有记忆条目。损坏文件跳过并告警（不抛异常）。"""
    if not os.path.isdir(store_dir):
        return []
    entries: list[MemoryEntry] = []
    for fname in os.listdir(store_dir):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(store_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            entry = _deserialize(text)
            if entry is not None:
                entries.append(entry)
            else:
                # 损坏文件 → 跳过并告警
                print(f"[WARN] memory: skipping corrupt entry file: {path}")
        except Exception as exc:
            print(f"[WARN] memory: cannot read {path}: {exc}")
    return entries


def delete_entry(store_dir: str, key: str) -> bool:
    """删除指定 key 的记忆条目，返回是否成功。"""
    path = _file_path(store_dir, key)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False