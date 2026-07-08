import pytest

from smile_harness.llm.base import LLM
from smile_harness.llm.mock import MockLLM


def test_mock_llm_returns_scripted_response():
    m = MockLLM(["frame1", "frame2"])
    assert m.complete([], []) == "frame1"
    assert m.complete([], []) == "frame2"
    with pytest.raises(StopIteration):
        m.complete([], [])


def test_mock_llm_empty_script_raises_immediately():
    m = MockLLM([])
    with pytest.raises(StopIteration):
        m.complete([], [])


def test_mock_llm_is_an_llm():
    assert isinstance(MockLLM(["x"]), LLM)
