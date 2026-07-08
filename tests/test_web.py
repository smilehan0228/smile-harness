"""T22: 薄 Web 前端测试 — FastAPI TestClient 集成测试。

测试 SmileHarness 设计主题聊天页的 UI 元素和后端 API。
使用 MockLLM 避免依赖真实 LLM API。
"""

import json
from unittest.mock import patch

from fastapi.testclient import TestClient
from smile_harness.web.server import app
from smile_harness.llm.mock import MockLLM

client = TestClient(app)


def _mock_llm_factory():
    """创建 MockLLM 用于测试。"""
    script = [json.dumps({"thought": "Task completed", "final": True})]
    return MockLLM(script)


def test_index_returns_html():
    """GET / 返回 HTML 聊天页。"""
    response = client.get("/")
    assert response.status_code == 200
    assert "SmileHarness" in response.text
    assert "text/html" in response.headers["content-type"]


@patch("smile_harness.creds.manager.CredentialManager.get")
def test_chat_returns_result(mock_get):
    """POST /chat 返回成功结果（MockLLM）。"""
    mock_get.return_value = None  # 无 API key → 回退 MockLLM
    response = client.post("/chat", json={"task": "test task"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "iterations" in data
    assert "feedback_history" in data
    assert "final_message" in data


@patch("smile_harness.creds.manager.CredentialManager.get")
def test_chat_empty_task(mock_get):
    """空 task 字段也能正常返回。"""
    mock_get.return_value = None
    response = client.post("/chat", json={"task": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@patch("smile_harness.creds.manager.CredentialManager.get")
def test_chat_missing_body(mock_get):
    """缺少 task 字段时默认空字符串。"""
    mock_get.return_value = None
    response = client.post("/chat", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@patch("smile_harness.creds.manager.CredentialManager.get")
def test_chat_feedback_history_serializable(mock_get):
    """feedback_history 已正确序列化（category 是字符串而非枚举）。"""
    mock_get.return_value = None
    response = client.post("/chat", json={"task": "test"})
    assert response.status_code == 200
    data = response.json()
    for fb in data["feedback_history"]:
        assert isinstance(fb["category"], str)
        assert "message" in fb
        assert "fix_hint" in fb
        assert "raw" in fb


def test_index_contains_chat_ui():
    """GET / 返回的 HTML 包含聊天 UI 元素。"""
    response = client.get("/")
    html = response.text
    assert "messages" in html
    assert "sendMessage" in html
    assert "sidebar" in html
    assert "btnSend" in html
    assert "chatInput" in html
    assert "convList" in html