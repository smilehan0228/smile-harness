"""T11 ReAct 决策解析器测试 — JSON→Decision, DecisionParseError。"""

import pytest

from smile_harness.llm.base import Decision, Action
from smile_harness.loop.decision import parse_decision, DecisionParseError


# ── 1. 合法 JSON → Decision with action ──────────────────────────────

def test_parse_valid_react():
    raw = '{"thought": "need to read file", "action": "read_file", "action_input": {"path": "src/main.py"}, "final": false}'
    decision = parse_decision(raw)
    assert decision.thought == "need to read file"
    assert decision.final is False
    assert decision.action is not None
    assert decision.action.name == "read_file"
    assert decision.action.args == {"path": "src/main.py"}


# ── 2. final=true → Decision(final=True, action=None) ────────────────

def test_parse_final_decision():
    raw = '{"thought": "task completed", "final": true}'
    decision = parse_decision(raw)
    assert decision.thought == "task completed"
    assert decision.final is True
    assert decision.action is None


# ── 3. 缺 thought → DecisionParseError ───────────────────────────────

def test_missing_thought_raises():
    raw = '{"action": "read_file", "action_input": {"path": "x"}}'
    with pytest.raises(DecisionParseError):
        parse_decision(raw)


# ── 4. 非 final 缺 action → DecisionParseError ───────────────────────

def test_missing_action_when_not_final_raises():
    raw = '{"thought": "I need to do something", "final": false}'
    with pytest.raises(DecisionParseError):
        parse_decision(raw)


# ── 5. final=true 且有 action → DecisionParseError ───────────────────

def test_final_with_action_raises():
    raw = '{"thought": "done", "action": "read_file", "action_input": {"path": "x"}, "final": true}'
    with pytest.raises(DecisionParseError):
        parse_decision(raw)


# ── 6. action="" → DecisionParseError ────────────────────────────────

def test_empty_action_raises():
    raw = '{"thought": "need to do something", "action": ""}'
    with pytest.raises(DecisionParseError):
        parse_decision(raw)


# ── 7. ```json...``` 包裹 → 正确解析 ─────────────────────────────────

def test_markdown_code_block_stripped():
    raw = """```json
{"thought": "read file", "action": "read_file", "action_input": {"path": "x"}, "final": false}
```"""
    decision = parse_decision(raw)
    assert decision.thought == "read file"
    assert decision.action.name == "read_file"
    assert decision.action.args == {"path": "x"}


# ── 8. 无效 JSON → DecisionParseError ────────────────────────────────

def test_invalid_json_raises():
    raw = 'not even json at all {{{'
    with pytest.raises(DecisionParseError):
        parse_decision(raw)


# ── 9. final 字段正确设置 ────────────────────────────────────────────

def test_final_flag_detected():
    # final=false 显式
    d1 = parse_decision(
        '{"thought": "t", "action": "read_file", "action_input": {}, "final": false}'
    )
    assert d1.final is False

    # final 未设置（默认 false）
    d2 = parse_decision(
        '{"thought": "t", "action": "read_file", "action_input": {}}'
    )
    assert d2.final is False

    # final=true
    d3 = parse_decision('{"thought": "t", "final": true}')
    assert d3.final is True