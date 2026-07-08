"""T22: 薄 Web 前端测试 — FastAPI TestClient 集成测试。

测试 SmileHarness 设计主题聊天页的 UI 元素和后端 API。
"""

from fastapi.testclient import TestClient
from smile_harness.web.server import app

client = TestClient(app)


def test_index_returns_html():
    """GET / 返回 HTML 聊天页。"""
    response = client.get("/")
    assert response.status_code == 200
    assert "SmileHarness" in response.text
    assert "text/html" in response.headers["content-type"]


def test_chat_returns_result():
    """POST /chat 返回成功结果。"""
    response = client.post("/chat", json={"task": "test task"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "iterations" in data
    assert "feedback_history" in data
    assert "final_message" in data


def test_chat_empty_task():
    """空 task 字段也能正常返回。"""
    response = client.post("/chat", json={"task": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_chat_missing_body():
    """缺少 task 字段时默认空字符串。"""
    response = client.post("/chat", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_chat_feedback_history_serializable():
    """feedback_history 已正确序列化（category 是字符串而非枚举）。"""
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