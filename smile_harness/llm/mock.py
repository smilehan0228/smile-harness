"""MockLLM — 脚本化 ReAct 响应，支撑离线确定性单测。

按构造时传入的 `script`（ReAct JSON 帧列表）顺序返回；耗尽抛 `StopIteration`。
不解析、不联网，仅满足 `LLM` 接口契约。
"""

from __future__ import annotations

from smile_harness.llm.base import LLM


class MockLLM(LLM):
    """按脚本队列顺序返回 ReAct 帧的 mock LLM。

    构造:
        MockLLM(script: list[str], name: str | None = None)

    行为:
        `complete(messages, tools)` 忽略 messages/tools 内容（但接受以
        满足接口），依次返回 script 中的下一帧；脚本耗尽时抛 `StopIteration`。
    """

    def __init__(self, script: list[str], name: str | None = None) -> None:
        self._script: list[str] = list(script)
        self._index: int = 0
        self.name: str | None = name

    def complete(self, messages: list[dict], tools: list[dict]) -> str:
        # 接受 messages/tools 以满足 LLM 接口契约，但忽略其内容。
        if self._index >= len(self._script):
            raise StopIteration("MockLLM script exhausted")
        frame = self._script[self._index]
        self._index += 1
        return frame
