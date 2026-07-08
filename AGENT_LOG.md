# AGENT_LOG.md — smile-harness

> 按时间序记录关键节点。每条：时间戳 / task / Superpowers 技能 / prompt-context 配置 / subagent 输出或 commit / 人工干预 / 教训。

---

## 2026-07-08 — brainstorming → writing-plans → 冷启动

- **时间**：2026-07-08
- **阶段**：brainstorming（`brainstorming` 技能）→ writing-plans（`writing-plans` 技能）→ 冷启动验证（§4.5）
- **主开发智能体**：Claude Code + glm-5.2
- **关键 prompt/context 配置**：分四批 AskUserQuestion 逐块签字；每批汇总沉淀；不写实现代码。
- **产出**：
  - `SPEC.md`（11 节，含 A.5 领域与机制设计）
  - `PLAN.md`（20 task，标注依赖与并行波段）
  - `COLDSTART_PROMPT.md`（冷启动简报，工具无关）
  - `SPEC_PROCESS.md`（brainstorming 全程 + 冷启动节）
  - 项目记忆 `smile-harness-project.md`
- **冷启动**：
  - 方：**opencode + deepseek-v4-pro**（与主方 Claude Code 不同类型，合规 §4.5）
  - 全新 session、不导 memory、仅给 SPEC+PLAN+COLDSTART_PROMPT，跑 T3→T5
  - 结果：10/10 测试通过；暴露 7 处 SPEC/PLAN 缺陷（6 处 spec 写错、1 处弹性致歧义）
  - 产出存 `E:\agent\coldStart\`（`COLD_START_REPORT.md`、`IMPLEMENTATION_SUMMARY.md` + 源码）
- **人工干预**：主 agent 据冷启动反馈修订 SPEC §3 M4/M5、§6、§11 与 PLAN T2/T3/T5（见 SPEC_PROCESS.md §五 diff）。冷启动方自创的合理决策（8 类、匹配顺序、blocked 语义、stateless、project_root 参数、未知动作→danger）被采纳进 SPEC。
- **教训**：
  1. 接口签名、字段语义、依赖关系、枚举值必须在 SPEC/PLAN 写死，不能留弹性——弹性在 brainstorming 像宽容，在实现处就是歧义。
  2. 主 agent 自审发现不了"未明文写死的契约缺口"，因带隐性上下文会自动脑补；冷启动的零上下文才暴露这些。
  3. 网络受限（GitHub 不可达）使 Open Design 具体套件名未能锁定，留为 §10 未决。
- **下一步**：冷启动通过，进入 Band A（T0→T1）真实实现。每 task 一个 worktree→一个 PR，TDD 先红再绿再重构，PLAN.md 标 commit hash。

---

## 2026-07-08 — T0 仓库骨架（subagent-driven）

- **时间**：2026-07-08
- **task**：T0（Band A）
- **技能**：`using-git-worktrees` + `subagent-driven-development` + `test-driven-development`
- **subagent**：general-purpose，isolation=worktree，分支 `worktree-agent-afac76b25924fbf66`
- **产出**：`pyproject.toml`、`Makefile`、`.gitlab-ci.yml`（`unit-test` job）、`smile_harness/__init__.py`、`tests/__init__.py`、`tests/test_smoke.py`
- **关键 prompt 配置**：给 subagent T0 规格 + TDD 纪律 + "不写机制逻辑" + 报告格式
- **subagent 关键输出**：主动发现 pytest 9 空 suite→exit 5 与 T0 门禁冲突；**正确拒绝** conftest exit-5→0 hook（会掩盖真回归）；透明记录后提交。commit `40bc0fd`
- **人工干预（review-fix）**：两阶段评审通过；判定 subagent 把"加 conftest hook（坏）"与"加真实 smoke 测试（好）"混淆。发回 fix：加 `tests/test_smoke.py`（导入包断言版本）→ exit 0、CI 从起即绿、不掩盖回归。subagent amend → commit `4092176`
- **合并**：fast-forward merge 到 main，推送 origin，清理 worktree
- **commit hash**：`4092176`（main）
- **教训**：
  1. SPEC/PLAN 的"验证步骤"须考虑工具实际行为（pytest 空 suite exit 5），不能想当然写"退出 0（0 用例）"——已据实修订 PLAN T0。
  2. subagent 的判断力可信任（识别不可满足门禁 + 拒绝有害 hack），但需主 agent 复核其"拒绝"是否漏掉了正确替代方案（smoke test）。
  3. Windows 本地无 `make`，CI Linux 有；本地用 `pytest -q` 验，README 须说明。
- **下一步**：T1（LLM 抽象层 + mock），依赖 T0，串行。

---

## 2026-07-08 — T1 LLM 抽象层 + MockLLM（subagent-driven, 首个 gh PR）

- **时间**：2026-07-08
- **task**：T1（Band A）
- **技能**：`using-git-worktrees` + `subagent-driven-development` + `test-driven-development`
- **subagent**：general-purpose，isolation=worktree，分支 `worktree-agent-ae22bf456ca070435`
- **产出**：`smile_harness/llm/base.py`（`Action`/`Decision` dataclass + `LLM` ABC）、`smile_harness/llm/mock.py`（`MockLLM`）、`tests/test_mock_llm.py`（3 tests）
- **TDD**：红（`cannot import name 'LLM'`）→ 绿（4 passed）
- **subagent 关键输出**：commit `30ba081`；主动发现并报告 stale editable install（冷启动 `pip install -e .` 残留，影子化包解析），未擅自改全局环境，仅透明记录。无功能偏差。
- **人工干预**：两阶段评审通过（base/mock/test 干净，docstring 引用 SPEC §6，spec 合规+代码质量双✅）；卸载 stale editable install（`pip uninstall smile-harness`）消除后续 worktree 解析隐患。
- **PR 工作流**：gh CLI 已装+授权（smilehan0228）；`gh pr create` → PR #1 → `gh pr merge --squash --delete-branch` → main `bf9eef3`。首个 gh 端到端跑通。
- **commit hash**：`bf9eef3`（main，squash）
- **教训**：
  1. 冷启动/探针环境的 `pip install -e .` 会留下 stale editable install 影子化正式仓库——须在切换到正式开发前卸载。
  2. gh `--delete-branch` 会尝试删本地分支，若 worktree 仍持有该分支会报错；须先 `git worktree remove` 再 `git branch -D`（顺序很重要）。
- **下一步**：Band B 并行（T2/T3/T5/T8/T9/T10，6 个 subagent 并发 worktree）；T6 待 T5 完成后启动。

---

## 2026-07-08 — T2 工具四件套 + 分发（subagent-driven）

- **时间**：2026-07-08
- **task**：T2（Band B）
- **技能**：`using-git-worktrees` + `subagent-driven-development` + `test-driven-development`
- **subagent**：general-purpose，isolation=worktree，分支 `worktree-agent-a24d38bc3783a240f`
- **产出**：`smile_harness/tools/base.py`（`ToolResult`）、`fs.py`（`read_file/write_file/edit_file/list_dir`）、`shell.py`（`run_shell` + 12 项黑名单）、`dispatcher.py`（`Dispatcher` 路由）、`tests/test_tools.py`（9 tests）
- **TDD**：红（import error）→ 绿（13 passed, 4 existing + 9 new）
- **subagent 关键输出**：commit `efc6756`；设计决策——`edit_file` 用 old_str/new_str 语义（恰好一次出现才替换，防歧义）；`write_file` HITL 检查在 fs 层（非 dispatcher）；shell 黑名单大小写不敏感；Dispatcher 用 dict 路由 + `**action.args` 解包传参。
- **人工干预**：单阶段评审通过（代码干净，符合 SPEC）。GitHub 自动 squash merge PR #2→main `183b52f`；本地 `git reset --hard origin/main` 同步。
- **commit hash**：`183b52f`（main，PR #2 squash）
- **教训**：
  1. `gh pr merge` 在 worktree 内执行会因 main 被主 worktree 占用而失败；改在主仓库 fetch+merge 更稳。
  2. GitHub 在 PR 创建时可能自动合并（若 CI 已过），本地需 `reset --hard origin/main` 对齐。
- **下一步**：Band B 剩余（T3/T5/T8/T9/T10 可并行，T6 待 T5 后）。

---

## 2026-07-08 — Band B 批量并行（T3/T5/T8/T9/T10，5 个 subagent 并发 worktree）

- **时间**：2026-07-08
- **task**：T3, T5, T8, T9, T10（Band B）
- **技能**：`using-git-worktrees` + `subagent-driven-development` + `test-driven-development`
- **subagents**：5 个 general-purpose agent 并发，各自 isolation=worktree
- **产出**：

| Task | PR | Commit | 新增 | 测试 |
|------|-----|--------|------|------|
| T3 三级护栏 | #5 | `7db182d` | `guardrails/guardrail.py` | 22/22 (9 new) |
| T5 taxonomy | #3 | `2c2fdb5` | `feedback/taxonomy.py` | 22/22 (9 new) |
| T8 记忆 | #6 | `6b3af30` | `memory/store.py`, `retrieve.py` | 21/21 (8 new) |
| T9 配置 | #4 | `e331f4e` | `config/schema.py`, `loader.py` | 19/19 (6 new) |
| T10 凭据 | #7 | `c9a4403` | `creds/manager.py`, `keyring_store.py`, `env_store.py` | 31/31 (18 new) |

- **全量**：**63/63 tests passed**，0 回归。
- **人工干预**：单阶段评审通过所有 5 个 task；GitHub squash merge PR #3–#7；worktree 清理因 branch 被 worktree 持有所阻（非阻塞，后续手动清理）。
- **教训**：
  1. 5 个并发 worktree subagent 全部成功，无冲突——证明 Band B 的并行设计合理。
  2. `gh pr merge --delete-branch` 在 worktree 仍持分支时失败，但 merge 本身成功；后续需手动 `git worktree remove` 清理。
  3. T10 测试用自定义 `MemoryKeyring(KeyringBackend)` 替代 `keyring.backends.memory`（因当前 keyring 版本中该路径不可用），设计决策值得记录。
- **下一步**：Band C 集成——T6 校验器注册表（依赖 T5，可立即启动），T4 HITL（依赖 T3），T7 自纠闭环（依赖 T6+T2），T11 ReAct 解析（依赖 T1+T2+T3）。

---

## 2026-07-08 — Band C 集成（T4/T6/T11 并行 → T7 → T12 串行）

- **时间**：2026-07-08
- **task**：T4, T6, T11, T7, T12（Band C）
- **技能**：`using-git-worktrees` + `subagent-driven-development` + `test-driven-development`
- **subagents**：3 并发（T4/T6/T11）→ 1 串行（T7）→ 1 串行（T12）
- **产出**：

| Task | PR | Commit | 新增 | 测试 |
|------|-----|--------|------|------|
| T4 HITL | #9 | `1abc1a7` | `guardrails/hitl.py` | 74/74 (11 new) |
| T6 校验器 | #10 | `e5cdf18` | `feedback/validator.py`, `pytest_val.py`, `exitcode.py` | 72/72 (9 new) |
| T11 ReAct 解析 | #8 | `51090b9` | `loop/decision.py` | 72/72 (9 new) |
| T7 自纠闭环 | #11 | `3f16cb5` | `feedback/loop.py` | 106/106 (14 new) |
| T12 主循环 | #12 | `85b2063` | `loop/main_loop.py` | 118/118 (12 new) |

- **全量**：**118/118 tests passed**，0 回归。
- **机制演示（A.6）**：全部通过 ✅ 护栏拦截（rm -rf / write 越界）→ 反馈闭环（feedback 注入 context）→ 修复到全绿（write→pytest 失败→edit 修复→PASS）
- **人工干预**：单阶段评审通过所有 5 个 task；GitHub squash merge PR #8–#12。
- **教训**：
  1. Band C 依赖链设计合理：T4/T6/T11 无互相依赖可并行；T7 需 T6；T12 需全部。
  2. T12 作为集成点，测试驱动 3 个机制演示——MockLLM 脚本确定性复现，验证了所有核心模块的串联正确性。
  3. `gh pr merge` 在 worktree 内因分支被占用总是报 `--delete-branch` 失败，但 merge 本身成功——这是已知的 worktree 限制，不影响功能。
- **下一步**：Band D 前端/分发/部署（T13–T18）+ Band E 文档（T19–T20）。

---

## 2026-07-09 — Band D 批量推进（T13/T14/T15 并行 → T16 → T17 → T18 串行）

- **时间**：2026-07-09
- **task**：T13, T14, T15, T16, T17, T18（Band D）
- **技能**：`using-git-worktrees` + `subagent-driven-development` + `test-driven-development`
- **subagents**：3 并发（T13/T14/T15）→ 1（T16）→ 1（T17）→ 1（T18，含 rebase）
- **产出**：

| Task | PR | Commit | 新增 | 测试 |
|------|-----|--------|------|------|
| T13 机制演示 | #14 | `9783c2a` | `demo/demo_mechanisms.py`, `demo/broken_module/` | 119/119 (1 new) |
| T14 CLI | #15 | `fd98a7e` | `cli/app.py` (minicc) | 145/145 (26 new) |
| T15 薄 Web 前端 | #13 | `c2ea2fe` | `web/server.py` (FastAPI + chat) | 145/145 (27 new) |
| T16 打包分发 | #17 | `806eab5` | `Dockerfile`, `README.md`, `pyproject.toml` 元数据 | 158/158 (13 new) |
| T17 CI | #18 | `f530d26` | `.github/workflows/ci.yml`, `.gitlab-ci.yml` docker-build | 164/164 (6 new) |
| T18 云部署 | #16 | `6a2393a` | `deploy/docker-compose.yml`, `nginx.conf`, `deploy/README.md` | 172/172 (8 new) |

- **全量**：**172/172 tests passed**，0 回归。
- **人工干预**：
  - T13–T15 由前序 session 的 subagent 并行完成，单阶段评审通过，squash merge。
  - T16 由 subagent 完成，主 agent 在 worktree 验证 158/158 通过后 merge（PR #17）。
  - T17 由 subagent 完成，新增 `.github/workflows/ci.yml`（GitHub Actions: unit-test + docker-build）+ `.gitlab-ci.yml` docker-build job，164/164 通过后 merge（PR #18）。
  - T18 worktree 与 T16 Dockerfile 冲突：主 agent 手动 rebase T18 worktree 到 main（含 T16），保留 T16 Dockerfile（CLI 默认），T18 通过 docker-compose `command` 覆盖启动 uvicorn；更新 `test_dockerfile_valid` 适配；166/166 通过后 merge（PR #16）。
- **教训**：
  1. T16 和 T18 都创建 Dockerfile，但 PLAN 未标注此冲突——T18 依赖 T15 而非 T16 导致并行开发时文件冲突。实际合并时需 rebase + 手动解决。
  2. T18 的 docker-compose `command` 覆盖是良好的解耦模式：基础 Dockerfile 保持 CLI 默认，Web 部署通过 compose 文件注入命令。
  3. GitHub Actions 作为 `.gitlab-ci.yml` 的补充是务实选择——repo 在 GitHub 托管，GitLab CI 语法虽在但实际不会触发。
  4. T13 的 commit message 异常（"@" 而非规范格式），因 subagent 在 PR body 中使用了 `@` 字符导致 GitHub 截断。不影响功能，但需注意 PR body 避免首行特殊字符。
- **下一步**：Band E 文档——T19 AGENT_LOG.md（本条）更新、T20 REFLECTION.md 撰写。

---

## 2026-07-09 — T18 云部署实测 + T19/T20 收尾

- **时间**：2026-07-09
- **task**：T18 实际部署 + T19/T20 文档收尾
- **主 agent**：Claude Code（手动部署，非 subagent）

### T18 阿里云实际部署

- **服务器**：阿里云轻量应用服务器 2核2G，Ubuntu 24.04
- **公网 IP**：`101.37.170.172`
- **部署步骤**：
  1. 安装 Docker 29.1.3 + docker compose v2
  2. 配置 Docker 镜像加速器（`docker.m.daocloud.io`，因 Docker Hub 在国内被墙）
  3. `git clone` → `docker compose up -d --build`
  4. 开放阿里云防火墙 TCP 8000 端口
- **验证**：`curl http://101.37.170.172:8000/` → HTTP 200，返回 smile-harness 聊天页
- **容器状态**：`deploy-web-1` 运行中，`restart: unless-stopped`
- **教训**：
  1. 阿里云轻量服务器安全组默认不开放非标准端口，需手动添加防火墙规则
  2. Docker Hub 在国内不可达，必须配置 registry-mirrors
  3. T18 的"部署配置"和"实际部署"是两个阶段——PLAN 验收标准"公网 URL 可访问"需要实际部署才算完成

### T19/T20 收尾

- **T19 AGENT_LOG.md**：补全 T13–T18 及云部署实测记录
- **T20 REFLECTION.md**：~2200 字五章反思（项目概述/工作流/架构/AI 辅助开发/总结）
- **commit**：`72b4a26`、`0cc0f3f`

### 项目最终状态

- **全部 20 个 task 完成** ✅
- **172/172 tests passed**，0 回归
- **18 个 PR**，全部 squash merge
- **公网 WebUI**：http://101.37.170.172:8000/ 可访问

---

## 2026-07-09 — T21 真实 LLM 适配器（OpenAI 兼容 + DeepSeek 默认）

- **时间**：2026-07-09
- **task**：T21（Band D 之后的新 task）
- **主 agent**：Claude Code（直接实现，非 subagent）

### 背景

全部 20 个 task 完成后，唯一缺失的是真实 LLM 接入。`minicc task` 一直用 MockLLM 硬编码脚本，`config.llm` 和 `CredentialManager` 的基础设施已就绪但未被使用。

### 设计

- **新增** `smile_harness/llm/openai_compatible.py` — `OpenAICompatibleLLM` 实现 `LLM` 抽象接口，用 httpx 调用任意 OpenAI 兼容 API，零新依赖
- **修改** `smile_harness/cli/app.py` — `_run_task` 自动读取 `config.llm` + `CredentialManager.get(provider_api_key)`，有 key 走真实 LLM，无 key 回退 MockLLM
- **新增** `tests/test_real_llm.py` — 11 个单测（mock HTTP，不发起网络请求）
- **修改** `README.md` — 移除「仅 Mock LLM」，新增「配置真实 LLM」节

### 调试过程（4 轮 fix）

**第 1 轮：401 Authorization Required**

- 现象：`minicc task "创建 hello.py"` → HTTP 401
- 原因：API key 未配置或已过期
- 解决：用户 `minicc key set deepseek_api_key` 重新设置有效 key

**第 2 轮：SSL UNEXPECTED_EOF_WHILE_READING**

- 现象：httpx 报 SSL 握手错误
- 原因：临时网络波动（`curl.exe` 验证可直连 `api.deepseek.com`）
- 解决：重试后恢复，实际是 httpx 偶发 SSL 问题

**第 3 轮：400 Bad Request**

- 现象：认证通过但 API 拒绝请求
- 原因：`_build_tools()` 返回的 tools 格式是 `[{"name": "read_file", ...}]`，不符合 OpenAI function-calling 格式 `[{"type": "function", "function": {...}}]`，DeepSeek 拒绝
- 解决：在 `openai_compatible.py` 中检查 tools 格式，非 OpenAI 格式则跳过发送（ReAct 协议不依赖 function calling）

**第 4 轮：LLM 返回正确 JSON 但 agent 卡在重复 read_file**

- 现象：LLM 返回 `{"thought": "...", "action": "write_file", ...}` 格式正确，第一轮成功创建文件，但第 2-5 轮都在重复 `read_file` hello.py，不知道文件已存在
- 根因：`AgentLoop.run()` 中工具执行成功（`tool_result.ok=True`）时，结果**没有回灌**给 LLM。只有失败（`not ok`）或配置了 validator 时才记录 feedback。LLM 每轮都"失忆"
- 解决：工具成功时也追加 `FeedbackResult(category=PASS, ...)` 到 `feedback_history`（但不计入 `feedback_loop.record()`，避免误触发早停）

### 测试

- 13 个单测（11 适配器 + 2 tools 格式校验）
- 185/185 全绿，0 回归

### 教训

1. **OpenAI 兼容 ≠ 随便传**：API 对 tools 字段格式有严格要求，不符合即 400
2. **工具结果必须回灌**：没有 feedback 的 agent 就是盲人——MockLLM 模式掩盖了这个问题，因为脚本是预写的"知道"要做什么；真实 LLM 每轮都从零开始
3. **DEBUG 用 stderr 打印**：`print(..., file=sys.stderr)` 临时调试验证 LLM 返回内容，比加日志框架快
4. **feedback_history vs feedback_loop 的职责分离**：工具结果回灌只进 history（给 LLM 上下文），不进 loop（控制停机），否则一次成功工具调用就触发 PASS 停止

### 用户配置完整流程

```bash
minicc key set deepseek_api_key    # 存 API Key（隐藏输入）
minicc config init                 # 生成 config.yaml
minicc task "创建 hello.py"        # 有 key 走真实 LLM，无 key 回退 MockLLM
```

---

## 2026-07-09 — T23: 真实 LLM 集成修复（第 2 轮）— 打通 Web + CLI 端到端

- **时间**：2026-07-09 05:45–06:00
- **阶段**：T23 fix（真实 LLM 集成第 2 轮调试）
- **主开发智能体**：Claude Code + deepseek-v4-pro
- **触发**：用户反馈"前后端一起泡一下" + "本地希望接真实 LLM" + "minicc task 没有成功创建"

### 调试过程

**第 1 轮：Web 端仍用 MockLLM**

- 现象：`http://localhost:8000` 返回 "Task received: …"
- 原因：`server.py` 的 `/chat` 端点硬编码 `MockLLM`
- 解决：改为与 CLI 相同的逻辑——load config → 读 key → OpenAICompatibleLLM → 无 key 回退 MockLLM

**第 2 轮：config.yaml 和 key 都有，但仍走 MockLLM**

- 现象：端点返回仍是 MockLLM 的 "Task received: …"
- 调试：直接跑 Python 脚本验证 config 加载、key 读取、LLM 创建都 OK
- 根因：`AgentLoop.run()` 中 `_build_tools()` 返回的 tools 格式不符合 OpenAI function-calling 规范——T21 的"跳过发送"方案绕过了问题而非修复
- 解决：重写 `_build_tools()` 为 `{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}` 标准格式

**第 3 轮：LLM 返回 tool_calls 但代码不读**

- 现象：`RuntimeError: LLM returned empty content`
- 原因：DeepSeek 用原生 function calling 返回 `tool_calls` 数组，`openai_compatible.py` 只读 `content` 字段（此时为 null）
- 解决：`openai_compatible.py` 检查 `tool_calls`，存在时自动转换为 ReAct JSON 格式（`{"thought": ..., "action": "...", "action_input": {...}, "final": false}`）

**第 4 轮：parse_decision 拒绝 "final" 为字符串**

- 现象：LLM 返回 `{"thought": "…", "final": "Hello! …"}` 解析失败，`max_iters` 耗尽
- 原因：`parse_decision` 要求 `final` 必须是 boolean，但 LLM 经常直接返回答案文本
- 解决：容错处理——`final` 为字符串时视为 `final=True`，字符串内容作为 `thought`

**第 5 轮：工具结果不喂回 LLM**

- 现象：循环运行但 LLM 不知道工具执行结果，`max_iters` 耗尽
- 根因：`_organize_context` 每轮从 system prompt 重建 messages，历史对话丢失
- 解决：重构主循环——改为累积式 `messages` 列表，dispatch 后追加 `{"role": "user", "content": "Tool 'xxx' result: ..."}` 到对话历史。同时改进 system prompt 给出明确 JSON 格式示例

**第 6 轮：护栏误判 `/hello.py` 越界**

- 现象：`Status: blocked` — "write path outside project root: /hello.py"
- 原因：LLM 输出 Unix 风格路径 `/hello.py`，`_is_path_inside` 将其解析为 `E:\hello.py`（不在项目内）
- 解决：`guardrail._is_path_inside` + `dispatcher.dispatch` 都自动 strip 前导 `/` 和 `\`

**第 7 轮：Web 仍用 MockLLM（重启后才生效）**

- 现象：curl 测试通过但浏览器仍返回 MockLLM 结果
- 原因：uvicorn StatReload 只检测到第一次 `server.py` 改动，后续 `openai_compatible.py`、`main_loop.py`、`decision.py` 等的改动未触发重载
- 解决：手动重启 uvicorn

### 修改文件

| 文件 | 改动 |
|------|------|
| `smile_harness/llm/openai_compatible.py` | tool_calls → ReAct JSON 转换 |
| `smile_harness/loop/main_loop.py` | 累积式 messages + 工具结果回灌 + system prompt 优化 |
| `smile_harness/loop/decision.py` | final 字段容错（boolean / string） |
| `smile_harness/guardrails/guardrail.py` | `_is_path_inside` strip 前导斜杠 |
| `smile_harness/tools/dispatcher.py` | dispatch 时 strip 路径前导斜杠 |
| `smile_harness/web/server.py` | /chat 端点集成真实 LLM（load config → key → OpenAICompatibleLLM） |
| `tests/test_web.py` | mock `CredentialManager.get` 避免走真实 API |

### 测试

- 183/183 全绿
- CLI: `minicc task "create hello.py"` → `Status: success`，文件正确创建
- Web: `curl /chat '{"task": "1+1=?"}'` → `"1+1 equals 2"`（真实 DeepSeek 响应）

### 教训

1. **T21 的"跳过发送"方案是技术债**：当时 `_build_tools()` 格式不对，选择在 `openai_compatible.py` 中跳过发送而非修复格式——这导致 function calling 被禁用，LLM 只能用纯文本生成 JSON，容易出错。这次彻底修复了 tools 格式
2. **对话历史是 agent 的记忆**：每轮重建 messages 让 agent 变成金鱼——MockLLM 的预写脚本掩盖了这个问题，因为脚本"知道"每步做什么。真实 LLM 必须依赖累积的对话历史
3. **LLM 原生输出格式不可控**：`tool_calls` vs `content`、`final` 为 boolean vs string、路径 `/hello.py` vs `hello.py`——每一层都需要容错转换。不能让 LLM 的输出直接对接内部逻辑
4. **uvicorn --reload 不可靠**：多文件改动时可能漏掉一些文件，重启是最稳妥的

### 用户交互摘要

- 用户要求前后端一起跑 → 启动 uvicorn（HTML 内嵌在 server.py 中，无需分离启动）
- 用户要求本地接真实 LLM → 修改 server.py 的 `/chat` 端点
- 用户已存 key，要求验证 → curl 测试发现仍用 MockLLM → 深入调试
- 用户反馈 `minicc task` 没创建文件 → 发现 400 Bad Request → 修复 tools 格式
- 用户反馈 Web 仍用 MockLLM → 发现 uvicorn 未重载后续改动 → 重启解决

### CI 调试（第 8–10 轮，3 次 push 才过）

**第 8 轮：guardrail 只 strip path 不 strip root**

- 现象：CI Linux 上 `test_write_inside_root_is_safe` 失败 — `assert 'fatal' == 'safe'`
- 原因：`_is_path_inside` 只 strip 了 `path` 的前导 `/`，没 strip `root`。Linux 上 path 变相对路径而 root 保持绝对路径，解析到不同目录
- 解决：同时 strip path 和 root 的前导 `/`
- 结果：guardrail 测试通过，但其他 3 个测试仍失败

**第 9 轮：粗暴 strip 破坏了 Linux 绝对路径**

- 现象：CI 上 `test_demo`、`test_fixes_syntax_error_to_green`、`test_max_iters_stops` 失败，全部返回 `stopped`
- 原因：同时 strip path 和 root 后，`/tmp/xxx/mod.py` → `tmp/xxx/mod.py`（相对路径），`/tmp/xxx` → `tmp/xxx`（相对路径），两者在 CWD 下解析到不同位置，路径越界误判为 fatal
- 解决：改为两层检查——先按原路径解析判断，不通过再尝试 strip 前导 `/` 后判断

**第 10 轮：dispatcher 也 strip 导致文件写到错误位置**

- 现象：CI 仍失败，demo② 反馈 "File not found"
- 原因：dispatcher 对所有路径都 strip 前导 `/`，`/tmp/xxx/mod.py` → `tmp/xxx/mod.py`，文件写到了 CWD 下的 `tmp/xxx/mod.py` 而非 `/tmp/xxx/mod.py`
- 解决：dispatcher 还原为透传路径；guardrail 用两层检查；main_loop 中仅 strip 单层路径（`/hello.py` → `hello.py`），多层路径保留原样

### 最终修改文件（PR #21 squash）

| 文件 | 改动 |
|------|------|
| `smile_harness/llm/openai_compatible.py` | tool_calls → ReAct JSON 转换 |
| `smile_harness/loop/main_loop.py` | 累积式 messages + 工具结果回灌 + system prompt + 单层路径 strip |
| `smile_harness/loop/decision.py` | final 字段容错 |
| `smile_harness/guardrails/guardrail.py` | `_is_path_inside` 两层检查 |
| `smile_harness/web/server.py` | /chat 端点集成真实 LLM |
| `tests/test_web.py` | mock CredentialManager |

### 补充教训

5. **路径规范化要分层处理**：guardrail 负责验证（两层检查），main_loop 负责规范化（仅单层 strip），dispatcher 透传不修改。职责分离避免重复 strip 导致语义错误
6. **Windows 本地通过 ≠ Linux CI 通过**：`os.path.isabs`、路径解析、`/` 语义在 Windows 和 Linux 上完全不同，路径相关代码必须在 CI 上验证
7. **Squash merge 后中间 commit 的 log 更新会丢失**：本次 T23 的 AGENT_LOG.md 更新在原 commit `52f7a0c` 中，squash 后该 commit 消失，但内容被合并到 squash commit 中——本次追加的 CI 调试记录需要单独提交
