"""T13: 机制演示测试 — 验证 demo_mechanisms.py 运行成功（退出码 0）"""

import os
import subprocess
import sys


def test_demo_mechanisms_runs():
    """demo_mechanisms.py 运行成功（退出码 0）"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "demo/demo_mechanisms.py"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=project_root,
    )
    assert result.returncode == 0, (
        f"Demo failed with exit code {result.returncode}:\n"
        f"=== STDOUT ===\n{result.stdout}\n"
        f"=== STDERR ===\n{result.stderr}"
    )