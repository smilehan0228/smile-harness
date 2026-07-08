"""CredentialManager — 凭据管理器。主存储：keyring；兜底：.env 文件。"""

import re
import logging

from smile_harness.creds import keyring_store, env_store

logger = logging.getLogger(__name__)

# 仅允许字母、数字、下划线、连字符的 key 名
_KEY_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class CredentialManager:
    """凭据管理器。

    Args:
        service_name: keyring service 名，默认 "smile-harness"。
        env_file: .env 文件路径，默认 ".env"（项目根）。
    """

    def __init__(self, service_name: str = "smile-harness", env_file: str = ".env"):
        self._service = service_name
        self._env_file = env_file
        self._session_keys: set[str] = set()

    # ── 内部校验 ──────────────────────────────────────────────────────

    def _validate_key(self, key: str) -> None:
        """校验 key 名格式。"""
        if not key or not _KEY_NAME_RE.match(key):
            raise ValueError(
                f"无效的 key 名：'{key}'。仅允许字母、数字、下划线、连字符。"
            )

    # ── 公开接口 ──────────────────────────────────────────────────────

    def set(self, key: str, value: str) -> None:
        """设置凭据。keyring 不可用时写入 .env（并告警）。

        Args:
            key: 凭据 key 名。
            value: 凭据值。
        """
        self._validate_key(key)

        if keyring_store.is_available():
            keyring_store.set_keyring(self._service, key, value)
        else:
            logger.warning(
                "keyring 不可用，凭据 '%s' 将 fallback 写入 .env 文件", key
            )
            env_store.set_env(self._env_file, key, value)

        self._session_keys.add(key)
        logger.debug("凭据 '%s' 已设置", key)

    def get(self, key: str) -> str | None:
        """获取凭据。先查 keyring，再查 .env。

        Args:
            key: 凭据 key 名。

        Returns:
            凭据值，不存在时返回 None。
        """
        self._validate_key(key)

        # 先查 keyring
        if keyring_store.is_available():
            value = keyring_store.get_keyring(self._service, key)
            if value is not None:
                return value

        # fallback 到 .env
        return env_store.get_env(self._env_file, key)

    def show(self, key: str) -> str:
        """返回状态字符串（"已设置" / "未设置"），不回显明文。

        Args:
            key: 凭据 key 名。

        Returns:
            "已设置" 或 "未设置" 状态字符串。
        """
        self._validate_key(key)
        value = self.get(key)
        if value is not None:
            return "已设置"
        return "未设置"

    def clear(self, key: str) -> bool:
        """清除凭据。从 keyring 和 .env 都删。

        Args:
            key: 凭据 key 名。

        Returns:
            True 如果至少一处删除成功，False 如果两处都不存在。
        """
        self._validate_key(key)

        deleted_keyring = False
        deleted_env = False

        if keyring_store.is_available():
            deleted_keyring = keyring_store.delete_keyring(self._service, key)

        deleted_env = env_store.delete_env(self._env_file, key)

        if deleted_keyring or deleted_env:
            self._session_keys.discard(key)
            logger.debug("凭据 '%s' 已清除", key)
            return True
        return False

    def list_keys(self) -> list[str]:
        """列出所有已设置的 key 名称。

        Returns:
            key 名称列表。
        """
        keys = set(self._session_keys)

        # 从 .env 收集
        from pathlib import Path

        env_path = Path(self._env_file)
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or "=" not in stripped:
                    continue
                k = stripped.split("=", 1)[0].strip()
                if _KEY_NAME_RE.match(k):
                    keys.add(k)

        return sorted(keys)