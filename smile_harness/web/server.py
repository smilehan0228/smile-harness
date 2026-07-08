"""T15: 薄 Web 前端 — FastAPI 应用，提供 /chat 端点 + 极简聊天页。

会话状态服务端持有，使用内核库（AgentLoop + MockLLM）驱动。
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="smile-harness")

CHAT_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>smile-harness</title>
    <meta charset="utf-8">
    <style>
        body { font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 20px; }
        #messages { border: 1px solid #ccc; height: 400px; overflow-y: auto; padding: 10px; margin-bottom: 10px; }
        #input { width: 100%; padding: 8px; }
        .user { color: blue; }
        .agent { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>smile-harness</h1>
    <div id="messages"></div>
    <input id="input" type="text" placeholder="Enter your coding task..." onkeydown="if(event.key==='Enter')send()">
    <button onclick="send()">Send</button>
    <script>
        async function send() {
            const input = document.getElementById('input');
            const task = input.value.trim();
            if (!task) return;
            const msgs = document.getElementById('messages');
            msgs.innerHTML += '<div class="user">> ' + task + '</div>';
            input.value = '';
            try {
                const resp = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({task: task})
                });
                const data = await resp.json();
                msgs.innerHTML += '<div class="agent">' + JSON.stringify(data, null, 2) + '</div>';
            } catch(e) {
                msgs.innerHTML += '<div class="error">Error: ' + e.message + '</div>';
            }
            msgs.scrollTop = msgs.scrollHeight;
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回极简聊天 HTML 页。"""
    return CHAT_HTML


@app.post("/chat")
async def chat(request: Request):
    """接收任务，用 MockLLM 驱动 AgentLoop，返回结果。

    T15 阶段用 MockLLM（因为真实 LLM 尚未接入）。
    真实 LLM 接入后只需替换此处。
    """
    from smile_harness.loop.main_loop import AgentLoop, LoopConfig
    from smile_harness.llm.mock import MockLLM
    from smile_harness.tools.dispatcher import Dispatcher
    import json

    body = await request.json()
    task = body.get("task", "")

    # 用 MockLLM 做简单演示（写一个 final 响应）
    script = [json.dumps({"thought": f"Task received: {task}", "final": True})]
    llm = MockLLM(script)
    dispatcher = Dispatcher(".")
    loop = AgentLoop(llm=llm, dispatcher=dispatcher, config=LoopConfig())

    result = loop.run(task)

    # 转换 FeedbackResult 为可序列化格式
    result["feedback_history"] = [
        {
            "category": fb.category.value,
            "message": fb.message,
            "fix_hint": fb.fix_hint,
            "raw": fb.raw,
        }
        for fb in result["feedback_history"]
    ]
    return result