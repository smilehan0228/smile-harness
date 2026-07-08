"""T6: 校验器抽象 + 注册表 + FeedbackResult"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from smile_harness.feedback.taxonomy import Taxonomy


@dataclass
class FeedbackResult:
    """校验结果数据类。

    Attributes:
        category: 分类标签（Taxonomy 枚举）。
        message: 人类可读的摘要信息。
        fix_hint: 修复提示。
        raw: 原始输出（stdout+stderr）。
    """

    category: Taxonomy
    message: str
    fix_hint: str
    raw: str


class Validator(ABC):
    """校验器抽象基类。

    子类需要实现 validate 方法，对 target（文件路径或命令）运行校验，
    返回 FeedbackResult。
    """

    @abstractmethod
    def validate(self, target: str) -> FeedbackResult:
        """对 target 运行校验，返回 FeedbackResult。"""
        ...


class ValidatorRegistry:
    """校验器注册表。

    通过 name 注册和获取 Validator 实例，支持按名称调用校验。
    """

    def __init__(self) -> None:
        self._validators: dict[str, Validator] = {}

    def register(self, name: str, validator: Validator) -> None:
        """注册校验器。

        Args:
            name: 校验器名称，用于后续获取。
            validator: Validator 实例。
        """
        self._validators[name] = validator

    def get(self, name: str) -> Validator | None:
        """获取校验器。

        Args:
            name: 校验器名称。

        Returns:
            对应的 Validator 实例，不存在时返回 None。
        """
        return self._validators.get(name)

    def validate(self, name: str, target: str) -> FeedbackResult:
        """用指定校验器校验 target。

        Args:
            name: 已注册的校验器名称。
            target: 传给校验器的 target 参数。

        Returns:
            FeedbackResult 校验结果。

        Raises:
            KeyError: 如果 name 未注册。
        """
        validator = self._validators[name]
        return validator.validate(target)

    def list_names(self) -> list[str]:
        """列出所有已注册校验器名。

        Returns:
            已注册名称的列表。
        """
        return list(self._validators.keys())