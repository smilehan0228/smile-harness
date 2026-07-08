"""T21: 真实 LLM 适配器测试 — OpenAICompatibleLLM 单测。

测试方式：用 unittest.mock.patch 替换 httpx，验证请求构造和响应解析，
不发起真实网络请求。
"""

import json
from unittest import mock

import pytest

from smile_harness.llm.base import LLM
from smile_harness.llm.openai_compatible import OpenAICompatibleLLM


# ── helpers ─────────────────────────────────────────────────────────────


def _mock_response(content: str, status_code: int = 200) -> mock.MagicMock:
    """构建一个模拟的 httpx.Response。"""
    resp = mock.MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
    }
    resp.raise_for_status = mock.MagicMock()
    return resp


def _mock_error_response(message: str, status_code: int = 400) -> mock.MagicMock:
    """构建一个模拟的 API 错误响应。"""
    resp = mock.MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"error": {"message": message}}
    # raise_for_status 抛 HTTPError
    import httpx
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message, request=mock.MagicMock(), response=resp
    )
    return resp


# ── constructor tests ───────────────────────────────────────────────────


def test_openai_compatible_is_llm():
    """OpenAICompatibleLLM 是 LLM 的子类（接口合规）。"""
    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
    )
    assert isinstance(llm, LLM)


def test_constructor_stores_config():
    """构造函数正确存储各项配置。"""
    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        temperature=0.3,
    )
    assert llm._api_key == "sk-test"
    assert llm._base_url == "https://api.deepseek.com/v1"
    assert llm._model == "deepseek-chat"
    assert llm._temperature == 0.3


def test_constructor_default_temperature():
    """默认 temperature 为 0.0。"""
    llm = OpenAICompatibleLLM("sk-test", "https://api.deepseek.com/v1", "deepseek-chat")
    assert llm._temperature == 0.0


# ── complete() tests ────────────────────────────────────────────────────


def test_complete_returns_content():
    """complete() 从正常响应中提取 choices[0].message.content。"""
    llm = OpenAICompatibleLLM("sk-test", "https://api.deepseek.com/v1", "deepseek-chat")
    expected = '{"thought": "done", "final": true}'

    with mock.patch("httpx.post") as mock_post:
        mock_post.return_value = _mock_response(expected)
        result = llm.complete(
            [{"role": "user", "content": "hello"}],
            [{"type": "function", "function": {"name": "read_file"}}],
        )
        assert result == expected


def test_complete_sends_correct_request():
    """complete() 发出的 HTTP 请求包含正确的 model/messages/tools/temperature。"""
    llm = OpenAICompatibleLLM(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        temperature=0.7,
    )
    messages = [{"role": "user", "content": "fix the bug"}]
    tools = [{"name": "read_file"}]

    with mock.patch("httpx.post") as mock_post:
        mock_post.return_value = _mock_response('{"final": true}')
        llm.complete(messages, tools)

        # 验证请求参数
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["model"] == "deepseek-chat"
        assert call_kwargs["json"]["messages"] == messages
        assert call_kwargs["json"]["tools"] == tools
        assert call_kwargs["json"]["temperature"] == 0.7
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-test"
        assert call_kwargs["headers"]["Content-Type"] == "application/json"


def test_complete_url_constructed_correctly():
    """complete() 请求的 URL 是 base_url + /chat/completions。"""
    llm = OpenAICompatibleLLM("sk-test", "https://api.deepseek.com/v1", "deepseek-chat")

    with mock.patch("httpx.post") as mock_post:
        mock_post.return_value = _mock_response('{"final": true}')
        llm.complete([{"role": "user", "content": "hi"}], [])

        url = mock_post.call_args.args[0] if mock_post.call_args.args else mock_post.call_args.kwargs.get("url", "")
        assert url == "https://api.deepseek.com/v1/chat/completions"


def test_complete_base_url_trailing_slash_handled():
    """base_url 末尾有斜杠时不会出现双斜杠。"""
    llm = OpenAICompatibleLLM("sk-test", "https://api.deepseek.com/v1/", "deepseek-chat")

    with mock.patch("httpx.post") as mock_post:
        mock_post.return_value = _mock_response('{"final": true}')
        llm.complete([{"role": "user", "content": "hi"}], [])

        url = mock_post.call_args.args[0] if mock_post.call_args.args else mock_post.call_args.kwargs.get("url", "")
        assert url == "https://api.deepseek.com/v1/chat/completions"


def test_complete_http_error_raises():
    """HTTP 错误（如 401）→ 抛出 RuntimeError。"""
    llm = OpenAICompatibleLLM("sk-bad", "https://api.deepseek.com/v1", "deepseek-chat")

    with mock.patch("httpx.post") as mock_post:
        mock_post.return_value = _mock_error_response("Unauthorized", 401)
        with pytest.raises(RuntimeError, match="LLM API call failed"):
            llm.complete([{"role": "user", "content": "hi"}], [])


def test_complete_empty_response_raises():
    """空 choices 列表 → 抛出 RuntimeError。"""
    llm = OpenAICompatibleLLM("sk-test", "https://api.deepseek.com/v1", "deepseek-chat")

    with mock.patch("httpx.post") as mock_post:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"choices": []}
        resp.raise_for_status = mock.MagicMock()
        mock_post.return_value = resp

        with pytest.raises(RuntimeError, match="empty response"):
            llm.complete([{"role": "user", "content": "hi"}], [])


def test_complete_empty_content_raises():
    """choices[0].message.content 为空 → 抛出 RuntimeError。"""
    llm = OpenAICompatibleLLM("sk-test", "https://api.deepseek.com/v1", "deepseek-chat")

    with mock.patch("httpx.post") as mock_post:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"choices": [{"message": {"content": ""}}]}
        resp.raise_for_status = mock.MagicMock()
        mock_post.return_value = resp

        with pytest.raises(RuntimeError, match="empty content"):
            llm.complete([{"role": "user", "content": "hi"}], [])


def test_complete_api_error_response():
    """API 返回 error 字段 → 抛出 RuntimeError。"""
    llm = OpenAICompatibleLLM("sk-test", "https://api.deepseek.com/v1", "deepseek-chat")

    with mock.patch("httpx.post") as mock_post:
        resp = mock.MagicMock()
        resp.status_code = 400
        resp.json.return_value = {"error": {"message": "Invalid model"}}
        resp.raise_for_status = mock.MagicMock()
        mock_post.return_value = resp

        with pytest.raises(RuntimeError, match="LLM API error"):
            llm.complete([{"role": "user", "content": "hi"}], [])