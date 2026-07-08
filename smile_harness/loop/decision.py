"""ReAct 决策解析器 — 将 LLM 返回的 ReAct JSON 解析为 Decision 对象。"""

import json
import re

from smile_harness.llm.base import Decision, Action


class DecisionParseError(Exception):
    """决策解析失败。"""
    pass


def parse_decision(raw_response: str) -> Decision:
    """解析 LLM 返回的 ReAct JSON 响应为 Decision 对象。

    期望格式（ReAct 风格 JSON）:
    {
        "thought": "reasoning about what to do",
        "action": "read_file",
        "action_input": {"path": "src/main.py"},
        "final": false
    }

    或 final 响应:
    {
        "thought": "task completed",
        "final": true
    }

    Args:
        raw_response: LLM 返回的原始文本（可能包含 markdown 代码块包裹）。

    Returns:
        Decision 对象。

    Raises:
        DecisionParseError: JSON 无效、缺必填字段、action 与 final 冲突。
    """
    # 1. 提取 JSON：如果被 ```json ... ``` 包裹，提取内部
    json_str = _extract_json(raw_response)

    # 2. 解析 JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise DecisionParseError(f"Invalid JSON in response: {e}") from e

    if not isinstance(data, dict):
        raise DecisionParseError("Response must be a JSON object (dict)")

    # 3. 检查必填字段：thought 必须存在且为字符串
    if "thought" not in data:
        raise DecisionParseError("Missing required field 'thought'")
    thought = data["thought"]
    if not isinstance(thought, str):
        raise DecisionParseError("Field 'thought' must be a string")

    # 4. 确定 final 标志
    final = data.get("final", False)
    if not isinstance(final, bool):
        raise DecisionParseError("Field 'final' must be a boolean")

    if final:
        # 5. final=true 时不允许有 action
        if "action" in data and data["action"]:
            raise DecisionParseError("Cannot have 'action' when 'final' is true")
        return Decision(thought=thought, final=True, action=None)

    # 6. 非 final 时，必须提供 action
    action_name = data.get("action")
    if action_name is None:
        raise DecisionParseError("Missing required field 'action' when 'final' is not true")
    if not isinstance(action_name, str):
        raise DecisionParseError("Field 'action' must be a string")
    if action_name == "":
        raise DecisionParseError("Field 'action' cannot be an empty string")

    action_input = data.get("action_input", {})
    if not isinstance(action_input, dict):
        raise DecisionParseError("Field 'action_input' must be a JSON object (dict)")

    return Decision(
        thought=thought,
        action=Action(name=action_name, args=action_input),
        final=False,
    )


def _extract_json(raw_response: str) -> str:
    """从可能包含 markdown 代码块的文本中提取 JSON 字符串。"""
    # 匹配 ```json ... ``` 或 ``` ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_response.strip()