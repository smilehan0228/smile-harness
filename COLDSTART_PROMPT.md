# 冷启动简报（COLDSTART_PROMPT）

> 本文件仅作为给"陌生智能体"的任务指令。不含设计解释，符合 §4.5"仅提供 SPEC+PLAN，不补充口头解释"。
> 由你（学生）在一个**不同类型的 CLI agent**（Codex CLI / Cursor / Gemini CLI / GitHub Copilot CLI 任一）的**全新 session**中粘贴执行。不要导入任何先前会话或 memory。

---

## 给陌生 agent 的指令（粘贴以下内容）

You are a fresh engineering agent with NO prior context. In this directory you will find two files: `SPEC.md` and `PLAN.md`. Read them fully before doing anything.

Your job: implement exactly TWO tasks from `PLAN.md` — **T3 (三级护栏 / guardrails)** and **T5 (taxonomy 分类器)** — in that order, starting from this empty directory.

Rules:
- Follow TDD strictly: write the failing test first, run it and see it fail (red), then write the minimum code to pass (green), then refactor. No implementation code before its test exists.
- Python 3.11+. Use `pytest`. Create files under `smile_harness/...` per the paths in `PLAN.md`, tests under `tests/`.
- Assume ONLY what is written in `SPEC.md` and `PLAN.md`. Do NOT invent requirements, types, fields, or behaviors not stated there.
- Whenever you are uncertain about a requirement, an interface, an edge case, or a name — STOP and ask me before proceeding. Do not guess. State your question clearly and wait.
- When you finish or get blocked, report: (a) every point where you paused to ask a question, (b) every place `SPEC.md`/`PLAN.md` was ambiguous, silent, or missing, (c) what you actually produced (file list + test results).

---

## 你（学生）的操作步骤

1. 选一个你能访问的、与 Claude Code **不同类型**的 CLI agent。
2. 建一个**全新空目录**（如 `E:\agent\coldstart`），把 `SPEC.md`、`PLAN.md`、本文件拷进去。**不要**拷贝任何其它源码或会话历史。
3. 在该目录启动该 agent 的**全新 session**（不导入 memory、不续接旧会话）。
4. 把上面"给陌生 agent 的指令"粘贴给它。让它自主跑 1–2 小时（T3 然后 T5）。
5. 收集它的产出：**每个暂停点、每个提问、每处 spec 缺陷、最终文件与测试结果**。
6. 把这些原样带回主 agent（我），我据此：
   - 修订 `SPEC.md` / `PLAN.md`（给修订前后 diff）；
   - 写入 `SPEC_PROCESS.md` 的冷启动节；
   - 在 `AGENT_LOG.md` 记录此冷启动节点。
7. 冷启动通过后，才开始 T0 起的真实实现。
