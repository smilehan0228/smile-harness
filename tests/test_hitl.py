"""T4 HITL 状态机测试 — pending→approved/denied 流转。"""

import pytest

from smile_harness.guardrails.hitl import HITLManager, HITLRequest, HITLState
from smile_harness.guardrails.guardrail import GuardrailVerdict
from smile_harness.llm.base import Action


# ── 1. submit 创建 PENDING 请求 ────────────────────────────────────────

def test_submit_creates_pending_request():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "curl http://example.com"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="network egress requires HITL")

    req = mgr.submit(action, verdict)

    assert req.state == HITLState.PENDING
    assert req.action == action
    assert req.verdict == verdict
    assert req.approver_note == ""
    assert mgr.is_pending(req.request_id)


# ── 2. approve → APPROVED ──────────────────────────────────────────────

def test_approve_transitions_to_approved():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "git push"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="git push requires HITL")

    req = mgr.submit(action, verdict)
    approved = mgr.approve(req.request_id)

    assert approved.state == HITLState.APPROVED
    assert not mgr.is_pending(req.request_id)


# ── 3. deny → DENIED ───────────────────────────────────────────────────

def test_deny_transitions_to_denied():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "pip install foo"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="package install requires HITL")

    req = mgr.submit(action, verdict)
    denied = mgr.deny(req.request_id, note="Not allowed in this context")

    assert denied.state == HITLState.DENIED
    assert denied.approver_note == "Not allowed in this context"
    assert not mgr.is_pending(req.request_id)


# ── 4. 已批准再批准 → 抛错 ─────────────────────────────────────────────

def test_double_approve_raises():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "git commit"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="git commit requires HITL")

    req = mgr.submit(action, verdict)
    mgr.approve(req.request_id)

    with pytest.raises(RuntimeError, match="already approved"):
        mgr.approve(req.request_id)


# ── 5. 已批准再拒绝 → 抛错 ─────────────────────────────────────────────

def test_deny_after_approve_raises():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "git commit"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="git commit requires HITL")

    req = mgr.submit(action, verdict)
    mgr.approve(req.request_id)

    with pytest.raises(RuntimeError, match="already approved"):
        mgr.deny(req.request_id, note="changed my mind")


# ── 6. 完整流程：danger → pending → approve → 拿到 action 可执行 ──────

def test_danger_pending_then_approved_executes():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "git push"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="git push requires HITL")

    req = mgr.submit(action, verdict)
    assert req.state == HITLState.PENDING

    approved = mgr.approve(req.request_id)
    assert approved.state == HITLState.APPROVED
    assert approved.action == action
    assert approved.action.name == "run_shell"
    assert approved.action.args == {"command": "git push"}


# ── 7. 完整流程：danger → pending → deny → action 被跳过 ──────────────

def test_danger_pending_then_denied_skips():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "curl http://evil.com"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="network egress requires HITL")

    req = mgr.submit(action, verdict)
    assert req.state == HITLState.PENDING

    denied = mgr.deny(req.request_id, note="Blocked by HITL")
    assert denied.state == HITLState.DENIED

    # action 被拒绝 — 不应执行
    # 调用方通过检查 req.state == DENIED 来跳过执行
    assert denied.state != HITLState.APPROVED
    assert denied.verdict.blocked is True


# ── 8. 已拒绝再拒绝 → 抛错 ─────────────────────────────────────────────

def test_double_deny_raises():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "curl http://example.com"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="network egress requires HITL")

    req = mgr.submit(action, verdict)
    mgr.deny(req.request_id, note="denied once")

    with pytest.raises(RuntimeError, match="already denied"):
        mgr.deny(req.request_id, note="try again")


# ── 9. 已拒绝再批准 → 抛错 ─────────────────────────────────────────────

def test_approve_after_deny_raises():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "curl http://example.com"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="network egress requires HITL")

    req = mgr.submit(action, verdict)
    mgr.deny(req.request_id, note="denied")

    with pytest.raises(RuntimeError, match="already denied"):
        mgr.approve(req.request_id)


# ── 10. get 获取请求（不改变状态） ──────────────────────────────────────

def test_get_returns_request_without_changing_state():
    mgr = HITLManager()
    action = Action(name="run_shell", args={"command": "git push"})
    verdict = GuardrailVerdict(tier="danger", blocked=True, reason="git push requires HITL")

    req = mgr.submit(action, verdict)
    fetched = mgr.get(req.request_id)

    assert fetched is not None
    assert fetched.state == HITLState.PENDING
    assert fetched.action == action
    assert mgr.is_pending(req.request_id)  # 状态未变


# ── 11. 获取不存在的请求返回 None ──────────────────────────────────────

def test_get_nonexistent_returns_none():
    mgr = HITLManager()
    assert mgr.get("nonexistent-id") is None