"""LLM 抽象层 — M1 决策封装的基础类型与抽象接口。

`LLM.complete` 返回 ReAct 风格 JSON 的原始响应文本（不解析，解析是 T11 的职责）。
真实供应商实现（DeepSeek 等）在后续 task 接入；此处只定义抽象与数据模型。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Action:
    """LLM 解析出的动作（对应 SPEC §6 `Action{name, args}`）。"""

    name: str
    args: dict = field(default_factory=dict)


@dataclass
class Decision:
    """单轮决策（对应 SPEC §6 `Decision{thought, action, final}`）。"""

    thought: str
    action: Action | None = None
    final: bool = False


class LLM(ABC):
    """LLM 供应商抽象。`complete` 返回原始响应文本（ReAct JSON 串），不做解析。"""

    @abstractmethod
    def complete(self, messages: list[dict], tools: list[dict]) -> str:
        """返回下一帧 ReAct JSON 响应文本。

        Args:
            messages: chat 消息列表（role/content）。
            tools: 可用工具描述列表。

        Returns:
            供应商/Mock 返回的原始响应文本字符串。
        """
        ...
