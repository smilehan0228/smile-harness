"""T7: 自纠闭环 — FeedbackLoop + 三停机条件 测试"""

import pytest
from smile_harness.feedback.taxonomy import Taxonomy
from smile_harness.feedback.validator import FeedbackResult
from smile_harness.feedback.loop import FeedbackLoop


def _make_result(category: Taxonomy) -> FeedbackResult:
    """快捷构造 FeedbackResult。"""
    return FeedbackResult(
        category=category,
        message=f"Test {category.value}",
        fix_hint="fix hint",
        raw="raw output",
    )


class TestFeedbackLoopPass:
    """成功停机条件测试。"""

    def test_pass_stops_success(self):
        """记录 PASS → should_stop 返回 True, reason='pass'"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        loop.record(_make_result(Taxonomy.PASS))

        should_stop, reason = loop.should_stop()
        assert should_stop is True
        assert reason == "pass"

    def test_pass_after_failure_stops_success(self):
        """失败→PASS → 成功停"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        loop.record(_make_result(Taxonomy.ASSERTION_FAIL))
        loop.record(_make_result(Taxonomy.PASS))

        should_stop, reason = loop.should_stop()
        assert should_stop is True
        assert reason == "pass"


class TestFeedbackLoopEarlyStop:
    """早停条件测试。"""

    def test_consecutive_same_category_early_stops(self):
        """连续 2 次 ASSERTION_FAIL → early_stop"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        loop.record(_make_result(Taxonomy.ASSERTION_FAIL))
        loop.record(_make_result(Taxonomy.ASSERTION_FAIL))

        should_stop, reason = loop.should_stop()
        assert should_stop is True
        assert reason == "early_stop"

    def test_different_categories_dont_early_stop(self):
        """交错不同 category → 不触发早停"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        loop.record(_make_result(Taxonomy.ASSERTION_FAIL))
        loop.record(_make_result(Taxonomy.SYNTAX_ERROR))

        should_stop, reason = loop.should_stop()
        assert should_stop is False
        assert reason == ""

    def test_single_failure_does_not_stop(self):
        """仅 1 次失败 → should_stop 返回 False"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        loop.record(_make_result(Taxonomy.RUNTIME_ERROR))

        should_stop, reason = loop.should_stop()
        assert should_stop is False
        assert reason == ""

    def test_custom_early_stop_threshold(self):
        """自定义 early_stop_threshold=3 → 连续 2 次不停，3 次才停"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=3)
        loop.record(_make_result(Taxonomy.ASSERTION_FAIL))
        loop.record(_make_result(Taxonomy.ASSERTION_FAIL))
        should_stop, reason = loop.should_stop()
        assert should_stop is False
        assert reason == ""

        loop.record(_make_result(Taxonomy.ASSERTION_FAIL))
        should_stop, reason = loop.should_stop()
        assert should_stop is True
        assert reason == "early_stop"


class TestFeedbackLoopMaxIters:
    """轮数到顶停机条件测试。"""

    def test_max_iters_stops(self):
        """达到 max_iters → 返回 True, reason='max_iters'"""
        loop = FeedbackLoop(max_iters=3, early_stop_threshold=2)
        loop.record(_make_result(Taxonomy.SYNTAX_ERROR))
        loop.record(_make_result(Taxonomy.RUNTIME_ERROR))
        loop.record(_make_result(Taxonomy.IMPORT_ERROR))

        should_stop, reason = loop.should_stop()
        assert should_stop is True
        assert reason == "max_iters"

    def test_max_iters_not_reached_continues(self):
        """未达到 max_iters → 继续"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        loop.record(_make_result(Taxonomy.SYNTAX_ERROR))
        loop.record(_make_result(Taxonomy.RUNTIME_ERROR))

        should_stop, reason = loop.should_stop()
        assert should_stop is False
        assert reason == ""


class TestFeedbackLoopHistory:
    """历史记录累积测试。"""

    def test_history_accumulates(self):
        """history 正确累积所有记录"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        r1 = _make_result(Taxonomy.SYNTAX_ERROR)
        r2 = _make_result(Taxonomy.RUNTIME_ERROR)
        r3 = _make_result(Taxonomy.PASS)

        loop.record(r1)
        loop.record(r2)
        loop.record(r3)

        assert loop.history == [r1, r2, r3]
        assert len(loop.history) == 3

    def test_iteration_counts_up(self):
        """iteration 正确递增"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        assert loop.iteration == 0

        loop.record(_make_result(Taxonomy.SYNTAX_ERROR))
        assert loop.iteration == 1

        loop.record(_make_result(Taxonomy.RUNTIME_ERROR))
        assert loop.iteration == 2

        loop.record(_make_result(Taxonomy.PASS))
        assert loop.iteration == 3


class TestFeedbackLoopDefaults:
    """默认参数测试。"""

    def test_default_max_iters(self):
        """默认 max_iters=5"""
        loop = FeedbackLoop()
        assert loop.max_iters == 5

    def test_default_early_stop_threshold(self):
        """默认 early_stop_threshold=2"""
        loop = FeedbackLoop()
        assert loop.early_stop_threshold == 2

    def test_custom_params(self):
        """自定义参数正确设置"""
        loop = FeedbackLoop(max_iters=10, early_stop_threshold=3)
        assert loop.max_iters == 10
        assert loop.early_stop_threshold == 3

    def test_empty_loop_continues(self):
        """无记录时 should_stop 返回 False"""
        loop = FeedbackLoop(max_iters=5, early_stop_threshold=2)
        should_stop, reason = loop.should_stop()
        assert should_stop is False
        assert reason == ""