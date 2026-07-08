""".env 兜底存储后端 — 明文写入 .env 文件（带警告注释）。"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ENV_WARNING = "# WARNING: plaintext credential, process environment visible"


def set_env(env_file: str, key: str, value: str) -> None:
    """写入凭据到 .env 文件。

    Args:
        env_file: .env 文件路径。
        key: 凭据 key 名。
        value: 凭据值（明文）。
    """
    env_path = Path(env_file)
    lines: list[str] = []

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=False)

    # 检查是否已有此 key 的行
    updated = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "":
            new_lines.append(line)
        elif stripped.startswith(f"{key}="):
            new_lines.append(f"{key}={value}  {_ENV_WARNING}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{key}={value}  {_ENV_WARNING}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def get_env(env_file: str, key: str) -> str | None:
    """从 .env 文件读取凭据。

    Args:
        env_file: .env 文件路径。
        key: 凭据 key 名。

    Returns:
        凭据值，不存在时返回 None。
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        if k.strip() == key:
            # 去掉尾部的警告注释
            val = v.strip()
            if _ENV_WARNING in val:
                val = val.replace(_ENV_WARNING, "").strip()
            return val

    return None


def delete_env(env_file: str, key: str) -> bool:
    """从 .env 文件删除凭据。

    Args:
        env_file: .env 文件路径。
        key: 凭据 key 名。

    Returns:
        True 如果删除成功，False 如果 key 不存在。
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return False

    lines = env_path.read_text(encoding="utf-8").splitlines(keepends=False)
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "" or "=" not in stripped:
            new_lines.append(line)
        elif stripped.startswith(f"{key}="):
            found = True
        else:
            new_lines.append(line)

    if found:
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return found