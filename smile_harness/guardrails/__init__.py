"""护栏模块 — 三级分类 fatal/danger/safe 纯函数 + HITL 审批状态机。"""

from smile_harness.guardrails.guardrail import guardrail, GuardrailVerdict
from smile_harness.guardrails.hitl import HITLManager, HITLRequest, HITLState

__all__ = [
    "guardrail",
    "GuardrailVerdict",
    "HITLManager",
    "HITLRequest",
    "HITLState",
]