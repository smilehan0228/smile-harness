"""T7: 自纠闭环 — FeedbackLoop + 三停机条件（pass / early_stop / max_iters）"""

from smile_harness.feedback.validator import FeedbackResult


class FeedbackLoop:
    """自纠闭环管理器。

    跟踪迭代历史，判断停机条件。

    停机条件（按优先级）：
    1. **成功停**：最近一次 FeedbackResult.category == Taxonomy.PASS
    2. **早停**：连续 early_stop_threshold 次出现相同 category（非 PASS）
    3. **轮数到顶**：iteration >= max_iters
    """

    def __init__(self, max_iters: int = 5, early_stop_threshold: int = 2) -> None:
        self.max_iters = max_iters
        self.early_stop_threshold = early_stop_threshold
        self._history: list[FeedbackResult] = []
        self._iteration: int = 0

    def record(self, result: FeedbackResult) -> None:
        """记录一轮反馈结果。"""
        self._history.append(result)
        self._iteration += 1

    def should_stop(self) -> tuple[bool, str]:
        """判断是否应该停机。

        Returns:
            (should_stop, reason)
            reason: "pass" / "early_stop" / "max_iters" / "" (继续)
        """
        if not self._history:
            return False, ""

        last = self._history[-1]

        # 1. 成功停：最近一次 PASS
        if last.category.value == "pass":
            return True, "pass"

        # 2. 早停：连续 early_stop_threshold 次相同 category（非 PASS）
        if self._iteration >= self.early_stop_threshold:
            recent = self._history[-self.early_stop_threshold:]
            if all(r.category == recent[0].category for r in recent):
                return True, "early_stop"

        # 3. 轮数到顶
        if self._iteration >= self.max_iters:
            return True, "max_iters"

        return False, ""

    @property
    def iteration(self) -> int:
        """当前迭代轮数。"""
        return self._iteration

    @property
    def history(self) -> list[FeedbackResult]:
        """所有轮次的反馈历史记录。"""
        return list(self._history)