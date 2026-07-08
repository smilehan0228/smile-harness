"""HITL 状态机 — danger 动作的人工审批流转。

HITLManager 接收 guardrail 返回的 danger verdict，暂停执行等待审批。
状态流转: PENDING → APPROVED / DENIED（终态不可再变）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from smile_harness.guardrails.guardrail import GuardrailVerdict
from smile_harness.llm.base import Action


class HITLState(Enum):
    """HITL 审批状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass
class HITLRequest:
    """HITL 审批请求。

    Attributes:
        action: 待审批的动作。
        verdict: 原始 guardrail 裁决。
        state: 当前审批状态（默认 PENDING）。
        approver_note: 审批备注（deny 时填写）。
        request_id: 唯一请求 ID（由 HITLManager 自动分配）。
    """

    action: Action
    verdict: GuardrailVerdict
    state: HITLState = HITLState.PENDING
    approver_note: str = ""
    request_id: str = ""


class HITLManager:
    """HITL 审批管理器。

    管理 danger 动作的审批队列。支持：
    - submit(action, verdict) → HITLRequest
    - approve(request_id) → HITLRequest (state=APPROVED)
    - deny(request_id, note) → HITLRequest (state=DENIED)
    - is_pending(request_id) → bool
    - get(request_id) → HITLRequest | None
    """

    def __init__(self) -> None:
        self._requests: dict[str, HITLRequest] = {}
        self._counter: int = 0

    def _next_id(self) -> str:
        """生成下一个唯一请求 ID。"""
        self._counter += 1
        return f"hitl-{self._counter:04d}"

    def submit(self, action: Action, verdict: GuardrailVerdict) -> HITLRequest:
        """提交 danger 动作到审批队列。

        Args:
            action: 待审批的动作。
            verdict: guardrail 返回的 danger 裁决。

        Returns:
            新创建的 HITLRequest（state=PENDING）。
        """
        req = HITLRequest(
            action=action,
            verdict=verdict,
            state=HITLState.PENDING,
            approver_note="",
            request_id=self._next_id(),
        )
        self._requests[req.request_id] = req
        return req

    def approve(self, request_id: str) -> HITLRequest:
        """批准指定请求。

        Args:
            request_id: 要批准的请求 ID。

        Returns:
            更新后的 HITLRequest（state=APPROVED）。

        Raises:
            ValueError: 请求不存在。
            RuntimeError: 请求已终态（APPROVED 或 DENIED）。
        """
        req = self._get_or_raise(request_id)
        if req.state == HITLState.APPROVED:
            raise RuntimeError(f"Request {request_id} is already approved")
        if req.state == HITLState.DENIED:
            raise RuntimeError(f"Request {request_id} is already denied")
        req.state = HITLState.APPROVED
        return req

    def deny(self, request_id: str, note: str = "") -> HITLRequest:
        """拒绝指定请求。

        Args:
            request_id: 要拒绝的请求 ID。
            note: 拒绝备注（可选）。

        Returns:
            更新后的 HITLRequest（state=DENIED）。

        Raises:
            ValueError: 请求不存在。
            RuntimeError: 请求已终态（APPROVED 或 DENIED）。
        """
        req = self._get_or_raise(request_id)
        if req.state == HITLState.APPROVED:
            raise RuntimeError(f"Request {request_id} is already approved")
        if req.state == HITLState.DENIED:
            raise RuntimeError(f"Request {request_id} is already denied")
        req.state = HITLState.DENIED
        req.approver_note = note
        return req

    def is_pending(self, request_id: str) -> bool:
        """检查请求是否仍在等待审批。

        Returns:
            True 如果请求存在且 state==PENDING，否则 False。
        """
        req = self._requests.get(request_id)
        return req is not None and req.state == HITLState.PENDING

    def get(self, request_id: str) -> HITLRequest | None:
        """获取请求（不改变状态）。

        Returns:
            HITLRequest 如果存在，否则 None。
        """
        return self._requests.get(request_id)

    def _get_or_raise(self, request_id: str) -> HITLRequest:
        """获取请求，不存在则抛出 ValueError。"""
        req = self._requests.get(request_id)
        if req is None:
            raise ValueError(f"Request {request_id} not found")
        return req