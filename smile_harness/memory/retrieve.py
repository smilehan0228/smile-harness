"""记忆检索 — 关键词匹配 + 最近排序。"""

from datetime import datetime

from smile_harness.memory.store import MemoryEntry, list_entries


def _tokenize(text: str) -> set[str]:
    """简易分词：按非字母数字切分，转小写。"""
    import re

    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def _match_score(entry: MemoryEntry, query_tokens: set[str]) -> int:
    """计算匹配分：query 中的 token 出现在 key 或 content 里的数量。"""
    target_tokens = _tokenize(entry.key) | _tokenize(entry.content)
    return len(query_tokens & target_tokens)


def retrieve(store_dir: str, query: str, n: int = 5) -> list[MemoryEntry]:
    """返回最相关的 n 条记忆。

    排序规则：
    1. 关键词匹配（query 中任意词出现在 entry.content 或 entry.key 中）优先
    2. 同匹配度按 updated_at 降序（最近更新在前）
    3. 截取前 n 条
    """
    entries = list_entries(store_dir)
    if not entries:
        return []

    query_tokens = _tokenize(query)

    # 计算每个条目的匹配分
    scored: list[tuple[int, datetime, MemoryEntry]] = []
    for entry in entries:
        score = _match_score(entry, query_tokens)
        try:
            ts = datetime.fromisoformat(entry.updated_at)
        except ValueError:
            ts = datetime.min
        scored.append((score, ts, entry))

    # 排序：匹配分降序，同分则时间降序
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    return [entry for _, _, entry in scored[:n]]