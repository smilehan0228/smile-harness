"""T22: 薄 Web 前端 — FastAPI 应用，提供 /chat 端点 + SmileHarness 设计聊天页。

会话状态服务端持有，使用内核库（AgentLoop + LLM）驱动。
前端基于 Open Design SmileHarness 主题，支持多会话管理、Markdown 渲染、反馈面板。
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="smile-harness")

CHAT_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SmileHarness</title>
  <style>
    /* ===========================================================
       SmileHarness Design Tokens
       =========================================================== */
    :root {
      --bg: #ffffff;
      --surface: #f3f4f6;
      --fg: #111827;
      --muted: #6b7280;
      --border: #e5e7eb;
      --accent: #3964fe;
      --accent-secondary: #5686fe;
      --code-bg: #f1f5f9;
      --radius: 8px;
      --radius-pill: 100px;
      --font-display: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
      --font-body: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
      --font-mono: Menlo, Monaco, Consolas, "Cascadia Mono", "Ubuntu Mono", "DejaVu Sans Mono", "Liberation Mono", "JetBrains Mono", "Fira Code", Cousine, "Roboto Mono", "Courier New", Courier, sans-serif, system-ui;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      width: 100%; height: 100%;
      overflow: hidden;
      background: var(--bg);
      color: var(--fg);
      font-family: var(--font-body);
      font-size: 15px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    /* ===========================================================
       App Shell
       =========================================================== */
    .app {
      display: flex;
      width: 100%; height: 100%;
    }

    /* ===========================================================
       Sidebar
       =========================================================== */
    .sidebar {
      width: 260px;
      min-width: 260px;
      height: 100%;
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      transition: margin-left 0.25s ease, opacity 0.25s ease;
      z-index: 10;
    }
    .sidebar.collapsed {
      margin-left: -260px;
      opacity: 0;
      pointer-events: none;
    }
    .sidebar-header {
      padding: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }
    .sidebar-logo {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      color: var(--fg);
      font-weight: 600;
      font-size: 18px;
      letter-spacing: -0.01em;
    }
    .sidebar-new-chat {
      margin: 0 12px 8px;
      flex-shrink: 0;
    }
    .btn-new-chat {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 10px 16px;
      background: rgba(0,0,0,0.04);
      border: 1px solid rgba(0,0,0,0.06);
      border-radius: var(--radius-pill);
      color: var(--fg);
      font-family: var(--font-body);
      font-size: 14px;
      font-weight: 500;
      letter-spacing: 0.02em;
      cursor: pointer;
      transition: background 0.15s;
    }
    .btn-new-chat:hover { background: rgba(0,0,0,0.08); }
    .btn-new-chat svg { opacity: 0.6; }

    .sidebar-conversations {
      flex: 1;
      overflow-y: auto;
      padding: 0 8px 8px;
    }
    .sidebar-conversations::-webkit-scrollbar { width: 4px; }
    .sidebar-conversations::-webkit-scrollbar-track { background: transparent; }
    .sidebar-conversations::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.06); border-radius: 4px; }

    .conv-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: var(--radius);
      cursor: pointer;
      transition: background 0.12s;
      font-size: 13px;
      color: var(--muted);
      letter-spacing: 0.01em;
      line-height: 1.3;
      overflow: hidden;
    }
    .conv-item:hover { background: rgba(0,0,0,0.04); color: var(--fg); }
    .conv-item.active { background: rgba(0,0,0,0.06); color: var(--fg); }
    .conv-item-text {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* ===========================================================
       Main Content
       =========================================================== */
    .main {
      flex: 1;
      height: 100%;
      display: flex;
      flex-direction: column;
      min-width: 0;
      background: var(--bg);
    }

    /* Top bar */
    .topbar {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 20px;
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
      background: var(--bg);
    }
    .btn-sidebar-toggle {
      width: 36px; height: 36px;
      display: grid;
      place-items: center;
      background: transparent;
      border: 0;
      border-radius: var(--radius);
      color: var(--muted);
      cursor: pointer;
      transition: background 0.12s, color 0.12s;
      flex-shrink: 0;
    }
    .btn-sidebar-toggle:hover { background: rgba(0,0,0,0.06); color: var(--fg); }
    .topbar-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--fg);
      letter-spacing: -0.01em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Messages area */
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 24px 0;
      scroll-behavior: smooth;
    }
    .messages::-webkit-scrollbar { width: 6px; }
    .messages::-webkit-scrollbar-track { background: transparent; }
    .messages::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.04); border-radius: 3px; }

    .msg-container {
      max-width: 768px;
      margin: 0 auto;
      padding: 0 24px;
    }
    .msg-row {
      display: flex;
      gap: 16px;
      padding: 16px 0;
    }
    .msg-row.user { flex-direction: row-reverse; }
    .msg-avatar {
      width: 32px; height: 32px;
      border-radius: 50%;
      flex-shrink: 0;
      display: grid;
      place-items: center;
      font-size: 14px;
    }
    .msg-avatar.ai {
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--muted);
      font-weight: 600;
      font-size: 12px;
    }
    .msg-avatar.user {
      background: var(--accent);
      color: #fff;
      font-weight: 600;
      font-size: 12px;
      letter-spacing: 0.02em;
    }
    .msg-bubble {
      max-width: 100%;
      min-width: 0;
    }
    .msg-row.user .msg-bubble {
      background: var(--surface);
      border-radius: 16px 16px 4px 16px;
      padding: 12px 16px;
      font-size: 15px;
      line-height: 1.6;
    }
    .msg-row.ai .msg-bubble {
      font-size: 15px;
      line-height: 1.7;
      color: var(--fg);
    }
    .msg-row.ai .msg-bubble p { margin-bottom: 12px; }
    .msg-row.ai .msg-bubble p:last-child { margin-bottom: 0; }
    .msg-row.ai .msg-bubble h1, .msg-row.ai .msg-bubble h2, .msg-row.ai .msg-bubble h3 {
      font-weight: 600;
      letter-spacing: -0.01em;
      margin: 20px 0 8px;
    }
    .msg-row.ai .msg-bubble h1 { font-size: 20px; }
    .msg-row.ai .msg-bubble h2 { font-size: 17px; }
    .msg-row.ai .msg-bubble h3 { font-size: 15px; }
    .msg-row.ai .msg-bubble ul, .msg-row.ai .msg-bubble ol {
      padding-left: 20px;
      margin-bottom: 12px;
    }
    .msg-row.ai .msg-bubble li { margin-bottom: 4px; }
    .msg-row.ai .msg-bubble strong { font-weight: 600; color: var(--fg); }
    .msg-row.ai .msg-bubble code {
      font-family: var(--font-mono);
      font-size: 13px;
      background: rgba(0,0,0,0.04);
      padding: 2px 6px;
      border-radius: 4px;
      color: var(--accent-secondary);
    }
    .msg-row.ai .msg-bubble pre {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      overflow-x: auto;
      margin: 12px 0;
      font-family: var(--font-mono);
      font-size: 13px;
      line-height: 1.6;
      color: var(--fg);
    }
    .msg-row.ai .msg-bubble pre code {
      background: transparent;
      padding: 0;
      color: inherit;
      font-size: inherit;
    }
    .msg-row.ai .msg-bubble pre::-webkit-scrollbar { height: 4px; }
    .msg-row.ai .msg-bubble pre::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.06); border-radius: 2px; }

    /* Feedback panel */
    .feedback-toggle {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
      cursor: pointer;
      background: none;
      border: 0;
      font-family: var(--font-body);
      padding: 2px 0;
    }
    .feedback-toggle:hover { color: var(--fg); }
    .feedback-panel {
      margin-top: 8px;
      padding: 12px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      font-size: 13px;
      line-height: 1.5;
      display: none;
    }
    .feedback-panel.open { display: block; }
    .feedback-item {
      padding: 6px 0;
      border-bottom: 1px solid var(--border);
    }
    .feedback-item:last-child { border-bottom: 0; }
    .feedback-category {
      font-weight: 600;
      color: var(--fg);
      margin-bottom: 2px;
    }
    .feedback-message { color: var(--muted); }

    /* Welcome screen */
    .welcome {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      flex: 1;
      padding: 48px 24px;
      text-align: center;
    }
    .welcome-title {
      font-size: 28px;
      font-weight: 600;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
      color: var(--fg);
    }
    .welcome-subtitle {
      font-size: 15px;
      color: var(--muted);
      max-width: 480px;
      line-height: 1.6;
      margin-bottom: 32px;
    }

    /* Input area */
    .input-area {
      flex-shrink: 0;
      padding: 0 24px 20px;
      max-width: 768px;
      margin: 0 auto;
      width: 100%;
    }
    .input-wrapper {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 8px 12px;
      transition: border-color 0.15s;
    }
    .input-wrapper:focus-within { border-color: rgba(0,0,0,0.12); }
    .input-textarea {
      width: 100%;
      min-height: 48px;
      max-height: 200px;
      background: transparent;
      border: 0;
      outline: 0;
      resize: none;
      color: var(--fg);
      font-family: var(--font-body);
      font-size: 15px;
      line-height: 1.6;
      padding: 4px 0;
    }
    .input-textarea::placeholder { color: var(--muted); }
    .input-textarea::-webkit-scrollbar { width: 4px; }
    .input-textarea::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.06); border-radius: 2px; }
    .input-toolbar {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 6px;
      padding-top: 4px;
      border-top: 1px solid transparent;
    }
    .input-wrapper:focus-within .input-toolbar { border-top-color: var(--border); }

    .btn-send {
      width: 32px; height: 32px;
      display: grid;
      place-items: center;
      background: var(--accent);
      border: 0;
      border-radius: 50%;
      color: #fff;
      cursor: pointer;
      transition: background 0.15s, transform 0.12s;
      flex-shrink: 0;
    }
    .btn-send:hover { background: var(--accent-secondary); }
    .btn-send:active { transform: scale(0.94); }
    .btn-send:disabled { opacity: 0.3; cursor: default; }
    .btn-send:disabled:hover { background: var(--accent); }

    /* Typing indicator */
    .typing-dot {
      display: inline-block;
      width: 6px; height: 6px;
      border-radius: 50%;
      background: var(--muted);
      animation: typingBounce 1.4s infinite ease-in-out both;
    }
    .typing-dot:nth-child(1) { animation-delay: 0s; }
    .typing-dot:nth-child(2) { animation-delay: 0.16s; }
    .typing-dot:nth-child(3) { animation-delay: 0.32s; }
    @keyframes typingBounce {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    /* Error message */
    .msg-row.error .msg-bubble {
      color: #dc2626;
      font-size: 14px;
      font-style: italic;
    }

    /* Responsive */
    @media (max-width: 768px) {
      .sidebar { position: fixed; left: 0; top: 0; bottom: 0; z-index: 20; }
      .sidebar.collapsed { margin-left: -260px; }
      .msg-container { padding: 0 16px; }
      .input-area { padding: 0 16px 12px; }
      .topbar { padding: 10px 16px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <!-- ============================================================
         Sidebar
         ============================================================ -->
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-header">
        <a class="sidebar-logo" href="#">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="8" cy="9" r="1.8" fill="var(--fg)"/>
            <circle cx="16" cy="9" r="1.8" fill="var(--fg)"/>
            <path d="M6 15c2.5 3 4.5 3.5 6 3.5s3.5-.5 6-3.5" stroke="var(--fg)" stroke-width="2" stroke-linecap="round"/>
          </svg>
          Smile
        </a>
      </div>

      <div class="sidebar-new-chat">
        <button class="btn-new-chat" id="btnNewChat">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <line x1="8" y1="3" x2="8" y2="13"/>
            <line x1="3" y1="8" x2="13" y2="8"/>
          </svg>
          新对话
        </button>
      </div>

      <div class="sidebar-conversations" id="convList">
        <div class="conv-item active" data-conv-id="0">
          <span class="conv-item-text">新对话</span>
        </div>
      </div>
    </aside>

    <!-- ============================================================
         Main Content
         ============================================================ -->
    <main class="main">
      <!-- Top bar -->
      <header class="topbar">
        <button class="btn-sidebar-toggle" id="btnSidebarToggle" aria-label="切换侧边栏">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <line x1="3" y1="5" x2="15" y2="5"/>
            <line x1="3" y1="9" x2="15" y2="9"/>
            <line x1="3" y1="13" x2="15" y2="13"/>
          </svg>
        </button>
        <span class="topbar-title" id="topbarTitle">Smile</span>
      </header>

      <!-- Messages / Welcome -->
      <div class="messages" id="messages">
        <div class="welcome" id="welcomeScreen">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style="margin-bottom:20px">
            <circle cx="19" cy="21" r="4" fill="var(--fg)"/>
            <circle cx="37" cy="21" r="4" fill="var(--fg)"/>
            <path d="M14 34c6 7 10 8 14 8s8-1 14-8" stroke="var(--fg)" stroke-width="2.5" stroke-linecap="round"/>
          </svg>
          <h1 class="welcome-title">有什么可以帮助你的？</h1>
          <p class="welcome-subtitle">
            SmileHarness — 你的智能编程助手
          </p>
        </div>

        <div class="msg-container" id="msgContainer" style="display:none;">
          <!-- Messages rendered by JS -->
        </div>
      </div>

      <!-- Input area -->
      <div class="input-area">
        <div class="input-wrapper">
          <textarea
            class="input-textarea"
            id="chatInput"
            placeholder="发送消息…"
            rows="1"
          ></textarea>
          <div class="input-toolbar">
            <button class="btn-send" id="btnSend" disabled aria-label="发送消息">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <line x1="2" y1="7" x2="11" y2="7"/>
                <polyline points="8 4 12 7 8 10"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>

  <script>
    (function () {
      // ============================================================
      // State
      // ============================================================
      var state = {
        conversations: [{ id: 0, title: '新对话', messages: [] }],
        activeConvId: 0,
        sidebarOpen: true
      };

      // ============================================================
      // DOM refs
      // ============================================================
      var sidebar = document.getElementById('sidebar');
      var btnSidebarToggle = document.getElementById('btnSidebarToggle');
      var btnNewChat = document.getElementById('btnNewChat');
      var convList = document.getElementById('convList');
      var messages = document.getElementById('messages');
      var welcomeScreen = document.getElementById('welcomeScreen');
      var msgContainer = document.getElementById('msgContainer');
      var chatInput = document.getElementById('chatInput');
      var btnSend = document.getElementById('btnSend');
      var topbarTitle = document.getElementById('topbarTitle');

      // ============================================================
      // Sidebar toggle
      // ============================================================
      btnSidebarToggle.addEventListener('click', function () {
        state.sidebarOpen = !state.sidebarOpen;
        sidebar.classList.toggle('collapsed', !state.sidebarOpen);
      });

      // ============================================================
      // New chat
      // ============================================================
      btnNewChat.addEventListener('click', function () {
        var newConv = { id: Date.now(), title: '新对话', messages: [] };
        state.conversations.unshift(newConv);
        state.activeConvId = newConv.id;
        renderConversations();
        switchToConv(newConv.id);
      });

      // ============================================================
      // Conversation list
      // ============================================================
      function renderConversations() {
        var activeConvs = state.conversations.filter(function (c) { return c.messages.length > 0 || c.id === state.activeConvId; });
        var html = '';
        activeConvs.forEach(function (c) {
          var activeClass = c.id === state.activeConvId ? ' active' : '';
          html += '<div class="conv-item' + activeClass + '" data-conv-id="' + c.id + '">' +
            '<span class="conv-item-text">' + escapeHTML(c.title) + '</span>' +
            '</div>';
        });
        convList.innerHTML = html;

        convList.querySelectorAll('.conv-item').forEach(function (el) {
          el.addEventListener('click', function () {
            var convId = parseInt(el.getAttribute('data-conv-id'), 10);
            switchToConv(convId);
          });
        });
      }

      function switchToConv(convId) {
        state.activeConvId = convId;
        var conv = state.conversations.find(function (c) { return c.id === convId; });
        if (!conv) {
          conv = state.conversations[0];
          state.activeConvId = conv.id;
        }

        topbarTitle.textContent = conv.title;

        if (conv.messages.length === 0) {
          welcomeScreen.style.display = '';
          msgContainer.style.display = 'none';
        } else {
          welcomeScreen.style.display = 'none';
          msgContainer.style.display = '';
          renderMessages(conv);
        }

        renderConversations();
        scrollToBottom();
      }

      // ============================================================
      // Render messages
      // ============================================================
      function renderMessages(conv) {
        var html = '';
        conv.messages.forEach(function (msg) {
          var isUser = msg.role === 'user';
          var isError = msg.role === 'error';
          var rowClass = isUser ? 'msg-row user' : (isError ? 'msg-row error' : 'msg-row ai');
          html += '<div class="' + rowClass + '">';
          html += '<div class="msg-avatar ' + (isError ? 'ai' : msg.role) + '">' + (isUser ? 'S' : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="8" cy="9" r="1.5" fill="currentColor"/><circle cx="16" cy="9" r="1.5" fill="currentColor"/><path d="M6 14c2.5 2.5 4.5 3 6 3s3.5-.5 6-3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>') + '</div>';
          html += '<div class="msg-bubble">' + msg.content + '</div>';
          html += '</div>';
        });
        msgContainer.innerHTML = html;

        // Attach feedback toggle listeners
        msgContainer.querySelectorAll('.feedback-toggle').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var panel = this.nextElementSibling;
            if (panel) {
              panel.classList.toggle('open');
              this.textContent = panel.classList.contains('open') ? '▾ 评审反馈' : '▸ 评审反馈';
            }
          });
        });
      }

      function escapeHTML(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
      }

      // ============================================================
      // Simple text-to-HTML formatter for agent responses
      // ============================================================
      function formatAgentResponse(text) {
        if (!text) return '<p><em>(empty response)</em></p>';

        // Escape HTML first
        text = escapeHTML(text);

        // Handle code blocks: ```...```
        var parts = [];
        var codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g;
        var lastIndex = 0;
        var match;
        while ((match = codeBlockRegex.exec(text)) !== null) {
          if (match.index > lastIndex) {
            parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
          }
          var lang = match[1] || '';
          var code = match[2].replace(/^\n+|\n+$/g, '');
          parts.push({ type: 'code', lang: lang, content: code });
          lastIndex = codeBlockRegex.lastIndex;
        }
        if (lastIndex < text.length) {
          parts.push({ type: 'text', content: text.slice(lastIndex) });
        }

        var html = '';
        parts.forEach(function (part) {
          if (part.type === 'code') {
            html += '<pre><code>' + part.content + '</code></pre>';
          } else {
            // Split text by double newlines for paragraphs
            var paragraphs = part.content.split(/\n\n+/);
            paragraphs.forEach(function (p) {
              var trimmed = p.trim();
              if (!trimmed) return;
              // Inline newlines become <br>
              var withBreaks = trimmed.replace(/\n/g, '<br>');
              // Basic markdown: **bold**, *italic*, `inline code`
              withBreaks = withBreaks.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
              withBreaks = withBreaks.replace(/\*(.+?)\*/g, '<em>$1</em>');
              withBreaks = withBreaks.replace(/`([^`]+)`/g, '<code>$1</code>');
              html += '<p>' + withBreaks + '</p>';
            });
          }
        });

        return html || '<p><em>(empty response)</em></p>';
      }

      // ============================================================
      // Build feedback HTML
      // ============================================================
      function buildFeedbackHTML(feedbackHistory) {
        if (!feedbackHistory || feedbackHistory.length === 0) return '';
        var html = '<button class="feedback-toggle">▸ 评审反馈 (' + feedbackHistory.length + ')</button>';
        html += '<div class="feedback-panel">';
        feedbackHistory.forEach(function (fb) {
          html += '<div class="feedback-item">';
          html += '<div class="feedback-category">' + escapeHTML(fb.category) + '</div>';
          html += '<div class="feedback-message">' + escapeHTML(fb.message) + '</div>';
          if (fb.fix_hint) {
            html += '<div class="feedback-message" style="margin-top:2px"><strong>建议:</strong> ' + escapeHTML(fb.fix_hint) + '</div>';
          }
          html += '</div>';
        });
        html += '</div>';
        return html;
      }

      // ============================================================
      // Send message (real API call)
      // ============================================================
      function sendMessage() {
        var text = chatInput.value.trim();
        if (!text) return;

        var conv = state.conversations.find(function (c) { return c.id === state.activeConvId; });
        if (!conv) {
          conv = state.conversations[0];
          state.activeConvId = conv.id;
        }

        welcomeScreen.style.display = 'none';
        msgContainer.style.display = '';

        conv.messages.push({ role: 'user', content: '<p>' + escapeHTML(text) + '</p>' });

        if (conv.messages.length === 1) {
          conv.title = text.length > 30 ? text.slice(0, 30) + '…' : text;
          topbarTitle.textContent = conv.title;
        }

        renderMessages(conv);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        updateSendButton();
        scrollToBottom();

        // Show typing indicator
        var typingHTML = '<div class="msg-row ai" id="typingIndicator">' +
          '<div class="msg-avatar ai"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="8" cy="9" r="1.5" fill="currentColor"/><circle cx="16" cy="9" r="1.5" fill="currentColor"/><path d="M6 14c2.5 2.5 4.5 3 6 3s3.5-.5 6-3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></div>' +
          '<div class="msg-bubble"><span class="typing-dot"></span> <span class="typing-dot"></span> <span class="typing-dot"></span></div>' +
          '</div>';
        msgContainer.insertAdjacentHTML('beforeend', typingHTML);
        scrollToBottom();

        // Call real API
        fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task: text })
        })
        .then(function (resp) {
          if (!resp.ok) throw new Error('HTTP ' + resp.status + ': ' + resp.statusText);
          return resp.json();
        })
        .then(function (data) {
          // Remove typing indicator
          var typing = document.getElementById('typingIndicator');
          if (typing) typing.remove();

          var aiContent = formatAgentResponse(data.final_message || '');
          if (data.iterations !== undefined) {
            aiContent += '<p style="font-size:12px;color:var(--muted);margin-top:4px">完成于 ' + data.iterations + ' 轮迭代</p>';
          }
          aiContent += buildFeedbackHTML(data.feedback_history);

          conv.messages.push({ role: 'ai', content: aiContent });
          renderMessages(conv);
          renderConversations();
          scrollToBottom();
        })
        .catch(function (err) {
          // Remove typing indicator
          var typing = document.getElementById('typingIndicator');
          if (typing) typing.remove();

          conv.messages.push({ role: 'error', content: '<p>请求失败: ' + escapeHTML(err.message) + '</p>' });
          renderMessages(conv);
          scrollToBottom();
        });
      }

      function scrollToBottom() {
        requestAnimationFrame(function () {
          messages.scrollTop = messages.scrollHeight;
        });
      }

      // ============================================================
      // Input handling
      // ============================================================
      chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        updateSendButton();
      });

      chatInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });

      function updateSendButton() {
        btnSend.disabled = !chatInput.value.trim();
      }

      btnSend.addEventListener('click', sendMessage);

      // ============================================================
      // Init
      // ============================================================
      renderConversations();
      chatInput.focus();
    })();
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
    """接收任务，用 LLM 驱动 AgentLoop，返回结果。"""
    from smile_harness.loop.main_loop import AgentLoop, LoopConfig
    from smile_harness.llm.mock import MockLLM
    from smile_harness.tools.dispatcher import Dispatcher
    from smile_harness.config import load_config
    from smile_harness.creds.manager import CredentialManager
    import json
    import os

    body = await request.json()
    task = body.get("task", "")

    # 尝试加载配置并创建真实 LLM
    config_path = "config.yaml"
    llm = None
    if os.path.exists(config_path):
        try:
            config = load_config(config_path)
            creds = CredentialManager()
            api_key = creds.get(f"{config.llm.provider}_api_key")
            if api_key:
                from smile_harness.llm.openai_compatible import OpenAICompatibleLLM
                llm = OpenAICompatibleLLM(
                    api_key=api_key,
                    base_url=config.llm.endpoint,
                    model=config.llm.model,
                    temperature=config.llm.temperature,
                )
        except Exception:
            pass  # 回退到 MockLLM

    # 回退到 MockLLM（无 API key 或创建失败）
    if llm is None:
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