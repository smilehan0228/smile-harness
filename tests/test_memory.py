"""T8 记忆模块测试 — 存储 + 检索。"""

import os
import time

import pytest

from smile_harness.memory.store import (
    MemoryEntry,
    delete_entry,
    list_entries,
    read_entry,
    write_entry,
)
from smile_harness.memory.retrieve import retrieve


# ── 夹具 ────────────────────────────────────────────────────────


@pytest.fixture
def store_dir(tmp_path):
    """返回一个临时 .harness/ 目录。"""
    d = str(tmp_path / ".harness")
    os.makedirs(d, exist_ok=True)
    return d


def _make_entry(key: str, kind: str, content: str, updated_at: str | None = None) -> MemoryEntry:
    return MemoryEntry(
        key=key,
        kind=kind,
        content=content,
        updated_at=updated_at or "2026-01-01T00:00:00",
    )


# ── 1. write → read roundtrip ───────────────────────────────────

def test_write_then_read_entry(store_dir):
    entry = _make_entry("test-key", "fact", "The sky is blue.")
    write_entry(store_dir, entry)

    got = read_entry(store_dir, "test-key")
    assert got is not None
    assert got.key == "test-key"
    assert got.kind == "fact"
    assert got.content == "The sky is blue."
    assert got.updated_at == "2026-01-01T00:00:00"


# ── 2. list all entries ─────────────────────────────────────────

def test_list_entries_returns_all(store_dir):
    e1 = _make_entry("a", "fact", "alpha")
    e2 = _make_entry("b", "decision", "bravo")
    e3 = _make_entry("c", "preference", "charlie")

    write_entry(store_dir, e1)
    write_entry(store_dir, e2)
    write_entry(store_dir, e3)

    entries = list_entries(store_dir)
    keys = {e.key for e in entries}
    assert keys == {"a", "b", "c"}


# ── 3. delete entry ─────────────────────────────────────────────

def test_delete_entry_removes(store_dir):
    entry = _make_entry("del-me", "fact", "data")
    write_entry(store_dir, entry)

    assert delete_entry(store_dir, "del-me") is True
    assert read_entry(store_dir, "del-me") is None


# ── 4. retrieve by keyword ──────────────────────────────────────

def test_retrieve_by_keyword(store_dir):
    e1 = MemoryEntry(
        key="python-style",
        kind="convention",
        content="Use snake_case for Python functions.",
        updated_at="2026-01-01T00:00:00",
    )
    e2 = MemoryEntry(
        key="java-style",
        kind="convention",
        content="Use camelCase for Java methods.",
        updated_at="2026-01-02T00:00:00",
    )
    e3 = MemoryEntry(
        key="deploy-steps",
        kind="fact",
        content="Deploy via docker compose up.",
        updated_at="2026-01-03T00:00:00",
    )

    write_entry(store_dir, e1)
    write_entry(store_dir, e2)
    write_entry(store_dir, e3)

    results = retrieve(store_dir, "python", n=3)
    keys = [r.key for r in results]
    # "python-style" should match because "python" appears in key
    assert "python-style" in keys


# ── 5. recent n ordering ────────────────────────────────────────

def test_recent_n_ordering(store_dir):
    e1 = _make_entry("old", "fact", "data", updated_at="2026-01-01T00:00:00")
    e2 = _make_entry("mid", "fact", "data", updated_at="2026-01-02T00:00:00")
    e3 = _make_entry("new", "fact", "data", updated_at="2026-01-03T00:00:00")

    write_entry(store_dir, e1)
    write_entry(store_dir, e2)
    write_entry(store_dir, e3)

    results = retrieve(store_dir, "data", n=3)
    # All match "data" equally; ordering should be by updated_at desc
    assert results[0].key == "new"
    assert results[1].key == "mid"
    assert results[2].key == "old"


# ── 6. security: no credentials stored ──────────────────────────

def test_no_credentials_stored(store_dir):
    entry = MemoryEntry(
        key="secrets",
        kind="fact",
        content="My api_key is abc123.",
        updated_at="2026-01-01T00:00:00",
    )
    with pytest.raises(ValueError, match="credential"):
        write_entry(store_dir, entry)


# ── 7. read nonexistent → None ──────────────────────────────────

def test_read_nonexistent_returns_none(store_dir):
    assert read_entry(store_dir, "no-such-key") is None


# ── 8. retrieve respects n limit ────────────────────────────────

def test_retrieve_respects_n_limit(store_dir):
    for i in range(10):
        e = MemoryEntry(
            key=f"entry-{i}",
            kind="fact",
            content=f"data {i}",
            updated_at=f"2026-01-{i+1:02d}T00:00:00",
        )
        write_entry(store_dir, e)

    results = retrieve(store_dir, "data", n=3)
    assert len(results) == 3