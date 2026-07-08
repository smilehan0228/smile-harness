"""keyring 存储后端 — 系统凭据库（Windows Credential Manager / macOS Keychain / Linux Secret Service）。"""

import logging

import keyring

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """keyring 是否可用。"""
    try:
        # 尝试获取一个不存在的凭据（不会抛异常，返回 None），
        # 但能验证 keyring 后端是否正常初始化。
        keyring.get_password("__smile_probe__", "__probe__")
        return True
    except Exception:
        logger.warning("keyring 不可用，将 fallback 到 .env", exc_info=True)
        return False


def set_keyring(service: str, key: str, value: str) -> None:
    """写入凭据到系统 keyring。

    Args:
        service: keyring service 名。
        key: 凭据 key 名。
        value: 凭据值（明文）。
    """
    keyring.set_password(service, key, value)


def get_keyring(service: str, key: str) -> str | None:
    """从系统 keyring 读取凭据。

    Args:
        service: keyring service 名。
        key: 凭据 key 名。

    Returns:
        凭据值，不存在时返回 None。
    """
    return keyring.get_password(service, key)


def delete_keyring(service: str, key: str) -> bool:
    """从系统 keyring 删除凭据。

    Args:
        service: keyring service 名。
        key: 凭据 key 名。

    Returns:
        True 如果删除成功，False 如果凭据不存在。
    """
    try:
        keyring.delete_password(service, key)
        return True
    except keyring.errors.PasswordDeleteError:
        return False