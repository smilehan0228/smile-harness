"""T10: 凭据管理测试 — keyring fake backend + .env 兜底。"""

import os
import tempfile

import pytest
import keyring
from keyring.backend import KeyringBackend

from smile_harness.creds.manager import CredentialManager
from smile_harness.creds import keyring_store, env_store


# ── in-memory fake keyring ─────────────────────────────────────────────────

class MemoryKeyring(KeyringBackend):
    """内存 keyring 后端，用于测试隔离。"""

    def __init__(self):
        super().__init__()
        self._store: dict[str, dict[str, str]] = {}

    def set_password(self, service: str, username: str, password: str):
        self._store.setdefault(service, {})[username] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get(service, {}).get(username)

    def delete_password(self, service: str, username: str):
        try:
            del self._store[service][username]
        except KeyError:
            raise keyring.errors.PasswordDeleteError("not found")


# ── fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _fake_keyring():
    """每个测试都使用内存 fake backend，隔离真实系统凭据库。"""
    original = keyring.get_keyring()
    keyring.set_keyring(MemoryKeyring())
    yield
    keyring.set_keyring(original)


@pytest.fixture
def tmp_env():
    """临时 .env 文件。"""
    fd, path = tempfile.mkstemp(suffix=".env", prefix="smile_creds_test_")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def manager(tmp_env):
    """以临时 .env 初始化的 CredentialManager。"""
    return CredentialManager(service_name="smile-test", env_file=tmp_env)


# ── 1. set/get with fake backend ───────────────────────────────────────────

def test_set_get_with_fake_backend(manager):
    """keyring fake backend 写入后读取应得到相同值。"""
    manager.set("api_key", "sk-abc123")
    assert manager.get("api_key") == "sk-abc123"


# ── 2. show 不回显明文 ─────────────────────────────────────────────────────

def test_show_does_not_echo_plaintext(manager):
    """show() 返回状态字符串，不能包含明文。"""
    manager.set("api_key", "sk-abc123")
    result = manager.show("api_key")
    assert "sk-abc123" not in result
    assert "已设置" in result


def test_show_on_unset_key(manager):
    """未设置的 key show() 返回未设置。"""
    result = manager.show("nonexistent")
    assert "未设置" in result


# ── 3. clear 后 get 返回 None ──────────────────────────────────────────────

def test_clear_sets_unset(manager):
    """clear 后 get 应返回 None。"""
    manager.set("api_key", "sk-abc123")
    assert manager.clear("api_key") is True
    assert manager.get("api_key") is None


def test_clear_returns_false_for_nonexistent(manager):
    """clear 不存在的 key 返回 False。"""
    assert manager.clear("nonexistent") is False


# ── 4. env fallback when keyring unavailable ────────────────────────────────

def test_env_fallback_when_keyring_unavailable(manager, monkeypatch):
    """模拟 keyring_store 不可用→写入 .env；然后从 .env 读取（fallback 读）。"""

    # 模拟 keyring 完全不可用
    monkeypatch.setattr(keyring_store, "is_available", lambda: False)
    monkeypatch.setattr(keyring_store, "set_keyring", lambda s, k, v: None)
    monkeypatch.setattr(keyring_store, "get_keyring", lambda s, k: None)
    monkeypatch.setattr(keyring_store, "delete_keyring", lambda s, k: True)

    manager.set("api_key", "sk-abc123")
    # 应该 fallback 写入 .env
    assert manager.get("api_key") == "sk-abc123"

    # clear 也应该能删掉 .env 中的
    assert manager.clear("api_key") is True
    assert manager.get("api_key") is None


# ── 5. list_keys ───────────────────────────────────────────────────────────

def test_list_keys_returns_all(manager):
    """list_keys 返回所有已设置的 key。"""
    manager.set("api_key", "sk-abc")
    manager.set("db_pass", "secret123")
    keys = manager.list_keys()
    assert "api_key" in keys
    assert "db_pass" in keys


def test_list_keys_empty(manager):
    """没有凭据时 list_keys 返回空列表。"""
    assert manager.list_keys() == []


# ── 6. invalid key name raises ─────────────────────────────────────────────

@pytest.mark.parametrize("bad_key", [
    "key with spaces",
    "key@name",
    "key/name",
    "key:name",
    "key.name",
    "key=name",
    "key,name",
    "key;name",
    "",
])
def test_invalid_key_name_raises(manager, bad_key):
    """含特殊字符或空的 key 名应抛出 ValueError。"""
    with pytest.raises(ValueError):
        manager.set(bad_key, "value")


# ── 7. get nonexistent returns None ────────────────────────────────────────

def test_get_nonexistent_returns_none(manager):
    """不存在的 key get 返回 None。"""
    assert manager.get("nonexistent") is None