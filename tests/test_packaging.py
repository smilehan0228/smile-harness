"""T16: 打包分发测试 — 验证 pyproject.toml 元数据完整性。"""

import os
import sys
from pathlib import Path

import pytest


# pyproject.toml 根路径（项目根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def _read_pyproject() -> str:
    """读取 pyproject.toml 内容。"""
    return PYPROJECT_PATH.read_text(encoding="utf-8")


def test_pyproject_exists():
    """pyproject.toml 文件存在。"""
    assert PYPROJECT_PATH.exists(), f"pyproject.toml not found at {PYPROJECT_PATH}"


def test_pyproject_has_minicc_entrypoint():
    """验证 pyproject.toml 有 minicc 脚本入口。"""
    content = _read_pyproject()
    assert "minicc" in content, "minicc entrypoint not found in pyproject.toml"
    assert "smile_harness.cli.app:main" in content, (
        "minicc should point to smile_harness.cli.app:main"
    )
    assert "[project.scripts]" in content, (
        "[project.scripts] section missing in pyproject.toml"
    )


def test_pyproject_has_required_fields():
    """验证 pyproject.toml 包含所有必填元数据字段。"""
    content = _read_pyproject()

    required_fields = [
        "name",
        "version",
        "description",
        "requires-python",
        "readme",
        "license",
        "classifiers",
    ]

    for field in required_fields:
        assert field in content, f"Required field '{field}' missing in pyproject.toml"


def test_pyproject_version_matches_package():
    """pyproject.toml 中的 version 与 smile_harness.__version__ 一致。"""
    import smile_harness

    content = _read_pyproject()
    # 简单提取 version 行
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("version"):
            # version = "0.1.0"
            pkg_version = line.split("=")[1].strip().strip('"')
            assert pkg_version == smile_harness.__version__, (
                f"pyproject.toml version {pkg_version} != "
                f"smile_harness.__version__ {smile_harness.__version__}"
            )
            break


def test_pyproject_python_requires_311_plus():
    """requires-python 指定 >=3.11。"""
    content = _read_pyproject()
    assert ">=3.11" in content, "requires-python should be >=3.11"


def test_pyproject_has_build_system():
    """pyproject.toml 包含 build-system 配置。"""
    content = _read_pyproject()
    assert "[build-system]" in content, "build-system section missing"
    assert "setuptools" in content, "setuptools should be the build backend"


def test_readme_exists():
    """README.md 文件存在。"""
    readme_path = PROJECT_ROOT / "README.md"
    assert readme_path.exists(), f"README.md not found at {readme_path}"


def test_readme_has_content():
    """README.md 有实质内容（至少 100 字符）。"""
    readme_path = PROJECT_ROOT / "README.md"
    content = readme_path.read_text(encoding="utf-8")
    assert len(content) > 100, f"README.md too short ({len(content)} chars)"


def test_dockerfile_exists():
    """Dockerfile 文件存在。"""
    dockerfile_path = PROJECT_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"


def test_dockerfile_has_expected_content():
    """Dockerfile 包含关键指令。"""
    dockerfile_path = PROJECT_ROOT / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    expected_instructions = [
        "FROM python:3.11-slim",
        "WORKDIR",
        "COPY pyproject.toml",
        "pip install",
        "COPY smile_harness/",
        "EXPOSE 8000",
        "CMD",
    ]

    for instruction in expected_instructions:
        assert instruction in content, (
            f"Dockerfile missing expected instruction: {instruction}"
        )


def test_gitignore_excludes_env():
    """.gitignore 排除 .env 文件。"""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    content = gitignore_path.read_text(encoding="utf-8")

    # 至少有一条 .env 规则
    assert ".env" in content, ".gitignore should exclude .env files"


def test_pip_install_editable():
    """pip install -e . 可以成功安装（editable mode）。"""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(PROJECT_ROOT)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"pip install -e . failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_minicc_help_runs():
    """minicc --help 可运行（退出码 0）。"""
    import subprocess

    result = subprocess.run(
        ["minicc", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"minicc --help failed:\nSTDERR:\n{result.stderr}"
    )
    assert "minicc" in result.stdout, "minicc --help should mention minicc"
    assert "task" in result.stdout, "minicc --help should mention task command"
    assert "config" in result.stdout, "minicc --help should mention config command"
    assert "key" in result.stdout, "minicc --help should mention key command"