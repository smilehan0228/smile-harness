"""T3 护栏模块测试 — 三级分类 fatal/danger/safe。"""

import pytest

from smile_harness.guardrails.guardrail import guardrail, GuardrailVerdict
from smile_harness.llm.base import Action


# ── 1. rm -rf / → fatal ─────────────────────────────────────────────

def test_rm_rf_is_fatal():
    verdict = guardrail(
        Action(name="run_shell", args={"command": "rm -rf /"}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "fatal"
    assert verdict.blocked is True


# ── 2. git push --force → fatal ─────────────────────────────────────

def test_git_push_force_is_fatal():
    verdict = guardrail(
        Action(name="run_shell", args={"command": "git push --force origin main"}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "fatal"
    assert verdict.blocked is True


# ── 3. curl egress → danger ─────────────────────────────────────────

def test_curl_egress_is_danger():
    verdict = guardrail(
        Action(name="run_shell", args={"command": "curl http://example.com"}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "danger"
    assert verdict.blocked is True


# ── 4. read_file → safe ─────────────────────────────────────────────

def test_read_is_safe():
    verdict = guardrail(
        Action(name="read_file", args={"path": "/tmp/project/foo.txt"}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "safe"
    assert verdict.blocked is False


# ── 5. write outside root → fatal ───────────────────────────────────

def test_write_outside_root_is_fatal():
    verdict = guardrail(
        Action(name="write_file", args={"path": "/etc/passwd"}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "fatal"
    assert verdict.blocked is True


# ── 6. write inside root → safe ─────────────────────────────────────

def test_write_inside_root_is_safe():
    verdict = guardrail(
        Action(name="write_file", args={"path": "/tmp/project/foo.txt"}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "safe"
    assert verdict.blocked is False


# ── 7. unknown action → danger ──────────────────────────────────────

def test_unknown_action_is_danger():
    verdict = guardrail(
        Action(name="fly_to_moon", args={}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "danger"
    assert verdict.blocked is True


# ── 8. empty action name → danger ───────────────────────────────────

def test_empty_action_is_danger():
    verdict = guardrail(
        Action(name="", args={}),
        project_root="/tmp/project",
    )
    assert verdict.tier == "danger"
    assert verdict.blocked is True


# ── 9. disabled danger rule allows ──────────────────────────────────

def test_disabled_danger_rule_allows():
    verdict = guardrail(
        Action(name="run_shell", args={"command": "curl http://example.com"}),
        project_root="/tmp/project",
        disabled_danger_rules={"egress"},
    )
    assert verdict.tier == "safe"
    assert verdict.blocked is False