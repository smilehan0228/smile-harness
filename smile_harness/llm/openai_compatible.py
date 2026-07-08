"""OpenAI 兼容 LLM 适配器 — 通过 HTTP 调用任意 OpenAI 兼容 API（DeepSeek 等）。

实现 `LLM` 抽象接口，用 httpx 发送 chat completion 请求，
返回 ReAct JSON 原始响应文本。
"""

from __future__ import annotations

import json

import httpx

from smile_harness.llm.base import LLM


class OpenAICompatibleLLM(LLM):
    """OpenAI 兼容的 LLM 适配器。

    通过 POST {base_url}/chat/completions 调用，支持 DeepSeek 等
    使用 OpenAI 兼容协议的供应商。

    Args:
        api_key: API 密钥（Bearer token）。
        base_url: API 基础 URL（如 https://api.deepseek.com/v1）。
        model: 模型名称（如 deepseek-chat）。
        temperature: 采样温度，默认 0.0。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature

    def complete(self, messages: list[dict], tools: list[dict]) -> str:
        """调用 chat completion API，返回 ReAct JSON 响应文本。

        将 OpenAI 原生 tool_calls 转换为 ReAct JSON 格式，
        确保与 parse_decision 兼容。

        Args:
            messages: chat 消息列表（role/content）。
            tools: 可用工具描述列表。

        Returns:
            ReAct JSON 字符串。

        Raises:
            RuntimeError: HTTP 错误、API 返回错误、或响应为空。
        """
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "messages": messages,
            "tools": tools,
            "temperature": self._temperature,
        }

        try:
            resp = httpx.post(url, json=body, headers=headers, timeout=60.0)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM API call failed: {e}") from e

        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"LLM API error: {data['error']}")

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("LLM returned empty response")

        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        # 如果 LLM 调用了工具，转换为 ReAct JSON 格式
        if tool_calls:
            tc = tool_calls[0]
            func = tc.get("function", {})
            action_name = func.get("name", "")
            try:
                action_input = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                action_input = {}

            # 生成 ReAct JSON
            react = {
                "thought": content or f"Calling {action_name}",
                "action": action_name,
                "action_input": action_input,
                "final": False,
            }
            return json.dumps(react)

        if not content:
            raise RuntimeError("LLM returned empty content")

        return content