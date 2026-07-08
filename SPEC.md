# SPEC.md — smile-harness

> *Spec-Driven, Subagent-Built, Human-Owned.*
> AI4SE 期末项目 A · Coding Agent Harness。本文件 = 通用要求 + A 文件拼接后的完整规约。

---

## §1 问题陈述

**要解决什么问题**：当 LLM 能完成大部分"思考"时，coding agent 的可靠性来自 LLM 之外的那层工程——harness。但现成 coding agent（Claude Code 等）多为黑盒或建于重框架之上，学习者难以看清"决策封装 / 工具 / 记忆 / 治理 / 反馈 / 配置"这六层工程如何各司其职，更难验证它们是否真的是代码而非提示词。

**目标用户**：想理解或二次开发 agent harness 的开发者与学生；需要一个能本地跑、能读、能改、能用 mock 离线测试的极简参照实现。

**为什么值得做**：把 `Agent = LLM + Harness` 这层工程透明化。本项目提供一个极简但真实的 Python coding agent harness（`smile-harness`），开源，六维度均有可运行最低实现，并以**反馈闭环**为深挖重点。所有机制落实为确定性代码，移除真实 LLM 后仍可被 mock 单测独立验证——这正是 A.4 的硬标准。

---

## §2 用户故事（INVEST）

1. **US1**：作为开发者，我想用 CLI 下达一个 coding 任务，让 agent 读写文件、跑测试、自纠到全绿，以便自动化修复小 bug。（独立 / 可协商 / 有价值 / 可估 / 可测 / 小）
2. **US2**：作为开发者，我想用 mock LLM 跑确定性单测，CI 能在无网络、无真实 LLM 时验证 harness 机制仍工作。
3. **US3**：作为审慎者，我想危险动作被护栏拦截并转人工审批（HITL），agent 不会误删文件或乱推 git。
4. **US4**：作为学习者，我想读 SPEC + 源码看清六维度如何分工，理解 harness 工程而非把 agent 当黑盒。
5. **US5**：作为使用者，我想用 YAML 声明工具开关 / 护栏规则 / 校验器选择 / 自纠轮数 / LLM 配置，不改代码即可约束 agent 行为。
6. **US6**：作为 Web 用户，我想通过浏览器聊天界面驱动 agent（满足通用交付 #9 的线上 WebUI）。
7. **US7**：作为凭据管理者，我想首次引导隐藏录入 key、查看时不回显明文、可更新与清除，确保 key 不泄露。

---

## §3 功能规约（按模块）

每项给出 输入 / 行为 / 输出 / 边界条件 / 错误处理。

### M1 决策封装（主循环 + LLM 抽象层）
- **输入**：用户任务字符串、配置、记忆注入项、上一轮反馈。
- **行为**：`organize_context → call_llm → parse_action → dispatch(经护栏) → reinject → stop_check`，循环直至停机。LLM 抽象层 `LLM.complete(messages, tools) → response`，可注入 mock 实现。动作协议为 **ReAct 风格 JSON tool-call**（thought / action / action_input）。
- **输出**：每轮一个 `Decision` 与 `Action`，最终一个停机结论。
- **边界**：单轮 LLM 调用失败重试 ≤2 次；动作解析失败回灌"格式错误"反馈让 LLM 重试。
- **错误处理**：LLM 异常 → 记录日志并终止本轮；解析异常 → 回灌纠错反馈，不计入自纠轮数。

### M2 工具（动作 / 工具）
- **输入**：`Action(name, args)`。
- **行为**：`read_file / write_file / edit_file(补丁式) / list_dir / run_shell`。
- **输出**：`ToolResult(ok, stdout/stderr/content, error)`。
- **边界**：写动作（write/edit）路径必须在项目根目录内，越界即由护栏拦截；`run_shell` 危险子串黑名单拦截。
- **错误处理**：文件不存在 / 权限不足 → `ToolResult(ok=False, error=...)` 回灌。

### M3 记忆（上下文与记忆）
- **输入**：当前任务与上下文关键词。
- **行为**：`.harness/*.md`（项目约定 / 历史决策 / 用户偏好）；自实现"最近 N 条 + 关键词匹配"检索；按需注入而非全量载入。
- **输出**：注入到 context 的记忆片段。
- **边界**：单轮注入量有 token 上限；不在记忆里存任何凭据。
- **错误处理**：记忆文件损坏 → 跳过该条并告警，不阻断主循环。

### M4 治理护栏
- **输入**：`Action` + `project_root: str`。
- **行为**：`guardrail(action, project_root) → GuardrailVerdict(tier, blocked, reason)`，**无状态纯函数**（仅 action + project_root，不访问文件系统，保证可 mock 单测）。三级：
  - **致命**：自动阻断且不可覆盖（如 `rm -rf /`、`DROP TABLE/DATABASE`、`git push --force`、写路径越界、`mkfs`/`dd`/`shutdown` 等）。
  - **危险**：转 HITL 状态机（pending → approved/denied）（如网络外发 `curl/wget`、git 写操作、未知动作、空命令/空路径）。
  - **安全**：放行（读、项目内写）。
- **输出**：`GuardrailVerdict`。`blocked=True` 统一表示"不可自动执行"——致命=拒绝，危险=转 HITL 暂停；`tier` 字段区分二者，由 T4 HITL 状态机消费 `tier==danger`。
- **边界**：致命级规则不可被配置关闭；危险级可配置。**需文件系统状态的规则（如"覆盖已存在文件"）不在纯 guardrail 内判定**，而在工具分发层（M2）于执行前检查文件存在性后转 HITL——以保证 guardrail 的无状态与可单测。
- **错误处理**：规则正则异常 → 默认按"危险"处理并告警；未知动作 → 默认"危险"。

### M5 反馈闭环（深挖维度）
- **输入**：产物（测试输出 / 命令 stdout+exit code）。
- **行为**：独立 `Validator` 模块，可插拔注册表，内置 `PytestValidator`（解析 exit code + traceback）与 `ExitCodeProbe`（任意命令 exit code）。解析产物 → 归入**固定的 8 类 taxonomy**（`SYNTAX_ERROR / IMPORT_ERROR / ASSERTION_FAIL / TIMEOUT / LINT_VIOLATION / PASS / RUNTIME_ERROR / UNKNOWN`，名称锁定）+ 生成修复提示 → 回灌 → 进入自纠循环：**N 轮上限（默认 5）+ 连续 2 轮同类失败早停 + 全绿成功停**。`classify(raw_output) → (Taxonomy, fix_hint)` 为纯函数，**按特异性从高到低匹配**，顺序锁定为：`SYNTAX_ERROR → IMPORT_ERROR → ASSERTION_FAIL → TIMEOUT → LINT_VIOLATION → PASS → RUNTIME_ERROR → UNKNOWN`（先匹配先返回，避免 `RUNTIME_ERROR` 的 "Error" 子串误吞 `SyntaxError` 等）。
- **输出**：`FeedbackResult{category, message, fix_hint, raw}`。
- **边界**：taxonomy 分类逻辑为确定性代码，可 mock 单测；校验器不依赖网络。
- **错误处理**：解析不出 → `unknown` 类，原样回灌 raw，仍计入轮数。

### M6 配置
- **输入**：`config.yaml`。
- **行为**：声明式约束五项——工具开关 / 危险动作规则（正则黑名单 + 路径围栏）/ 校验器选择与参数 / 自纠轮数上限 / LLM 供应商·模型·端点。
- **输出**：运行时 `Config` 对象注入各模块。
- **边界**：致命级护栏规则不可由配置关闭。
- **错误处理**：配置语法错误 → 拒绝启动并指明行号。

### M7 凭据
- **输入**：`minicc key set/show/clear`。
- **行为**：keyring → Windows Credential Manager 为主存储；`.env` 明文兜底（标注明文 + 进程环境可见风险）。首次运行引导隐藏录入；`show` 仅显状态不回显；可更新 / 清除。
- **输出**：凭据就绪状态。
- **边界**：key 绝不硬编码、不进 git、不进日志 / 终端 history / 明文配置文件。
- **错误处理**：keyring 不可用 → 回退 .env 并告警明文风险。

### M8 CLI
- **输入**：`minicc "<task>"`、`minicc config init|edit`、`minicc key set|show|clear`。
- **行为**：加载配置与凭据 → 实例化内核 → 运行主循环 → 打印事件日志。
- **输出**：终端事件流 + 最终结论。
- **边界**：无 key 且任务需真实 LLM → 引导录入或退出。

### M9 薄 Web 前端
- **输入**：浏览器聊天输入。
- **行为**：FastAPI + 极简聊天页，调用同一内核库；会话状态服务端持有。
- **输出**：流式事件回显。
- **边界**：仅是内核的另一个前端，不含独立业务逻辑；部署阿里云。
- **错误处理**：LLM 调用失败 → 前端显错误并保留会话。

---

## §4 非功能性需求

- **性能**：mock 单测套件 < 30s；单轮真实 LLM 往返延迟取决于供应商。
- **安全**：凭据威胁模型见 §7；护栏为代码非提示词；沙箱 working-dir 围栏；致命规则不可配置关闭。
- **可用性**：`pip install smile-harness` 或 `docker run` 一键起；CLI 与 Web 同内核同配置。
- **可观测性**：结构化事件日志（task / 动作 / 护栏判定 / 反馈分类 / 轮数）落盘，便于 AGENT_LOG 与调试。

---

## §5 系统架构

```
LLM 抽象层 (真实供应商 / mock) ──▶ 主循环 (决策封装 M1)
                                     │
          ┌──────────────────────────┼──────────────────────────┐
     工具分发 (M2)              护栏 (M4)                 校验器 (M5)
          │                        │                          │
   外部世界(文件/shell)        HITL 状态机            pytest / exit-code
          └──────────────────────────┴──────────────────────────┘
                                     │
                          反馈回灌 → 下一轮 / 停机
   记忆 (M3) ← 按需注入        配置 (M6) ← 声明式约束        凭据 (M7) ← 供 LLM 层
```

**数据流**：用户任务 + 配置 + 记忆 → 主循环组织 context → LLM 返回 ReAct JSON → 解析 Action → 护栏判定 →（放行）工具执行 /（危险）HITL 暂停 /（致命）阻断 → 产物 → 校验器分类回灌 → 停机判断 → 下一轮或结束。

**外部依赖**：DeepSeek（默认，OpenAI 兼容端点）/ pytest / Docker / 阿里云 / Open Design。

---

## §6 数据模型

- `Action{name: str, args: dict}` — LLM 解析出的动作。
- `ToolResult{ok: bool, content: str, error: str|None}` — 工具执行结果。
- `FeedbackResult{category: Taxonomy, message: str, fix_hint: str, raw: str}` — 校验器输出。
- `Taxonomy` — 枚举，固定 8 值：`SYNTAX_ERROR / IMPORT_ERROR / ASSERTION_FAIL / TIMEOUT / LINT_VIOLATION / PASS / RUNTIME_ERROR / UNKNOWN`。
- `GuardrailVerdict{tier: Literal["fatal","danger","safe"], blocked: bool, reason: str}` — 护栏判定；`blocked=True` 表示"不可自动执行"（致命=拒绝 / 危险=转 HITL），`tier` 区分二者。
- `Decision{thought: str, action: Action|None, final: bool}` — 单轮决策。
- `MemoryEntry{key: str, kind: str, content: str, updated_at: str}` — 记忆条目。
- `Config{tools, guardrail_rules, validators, max_iters, llm}` — 运行时配置。
- 约束：`Taxonomy` 为枚举，闭环停机条件只依赖 `FeedbackResult.category` 与轮数计数器。

---

## §7 凭据与分发设计

### 凭据
- **存储方案**：`keyring` → Windows Credential Manager 为主；`.env` 明文兜底（明文 + 进程环境可见风险写入本节）。
- **录入 / 更新 / 清除**：首次运行引导隐藏输入（不进 shell history）；`key show` 仅显"已设置 / 未设置"不回显；`key set` 覆盖；`key clear` 删除。
- **威胁模型与对策**：
  | 泄露路径 | 对策 |
  |---|---|
  | 硬编码进源码 | 代码审查 + git pre-commit 扫描 |
  | 进 git 历史 | `.gitignore` 含 `.env`；pre-commit 密钥扫描 |
  | 进日志 / 终端 history | 日志脱敏；隐藏输入；不 echo key |
  | 明文配置文件 | 主存 keyring；.env 仅兜底并标注风险 |

### 分发
- **形态**：PyPI 包（`pip install smile-harness`）+ Docker 镜像（单条 `docker build` + `docker run`）双形态。
- **目标平台 / 架构**：Python 3.11+，跨平台；Docker 镜像 linux/amd64。
- **目标机 key 安全配置**：README 写明 `minicc key set` 流程或挂载 keyring 卷；不要求用户写明文 .env。
- **已知限制**：依赖 Python 3.11+；真实 LLM 需用户自备 key；Windows keyring 依赖系统凭据管理服务。

---

## §8 技术选型与理由

- **Python**：LLM / 单测 / keyring 生态成熟，六维度原型快，mock 友好，适合"机制是代码"的快速验证。
- **DeepSeek 默认（OpenAI 兼容）**：国内可直连、合规友好、价低；抽象层可切其它供应商或 mock。
- **YAML** 配置；**pytest** 既作校验器内置解析对象，又作自身测试框架；**keyring**；**Docker + PyPI**；**阿里云** 部署。
- **前端**：薄 Web 前端采用 **Open Design**（nexu-io/open-design，依 §3.4 要求）。接入时从其提供的 design system 与 skill 中选用一套作为前端设计系统；基线保证以 design tokens（色彩 / 间距 / 字号阶）约束生成代码确保 UI 一致。**注**：SPEC 编写环境当前无法直达 GitHub，具体套件名于实现阶段接入仓库时确认（见 §10）。
- **动作协议**：ReAct 风格 JSON tool-call（thought / action / action_input），基于供应商 chat completion，不依赖供应商私有 function-calling，便于跨供应商与 mock。

---

## §9 验收标准

- 六维度（决策 / 工具 / 记忆 / 治理 / 反馈 / 配置）均有可运行最低实现；**深挖维度（反馈闭环）** 有 taxonomy + 自纠 + 早停的完整实现。
- **三项机制演示**（mock LLM 下确定性复现，A.6）：
  ① 护栏拦截一个危险动作；
  ② 注入一次失败，反馈闭环使 agent 收到反馈并据此改变下一步；
  ③ 重点维度行为：修错实现使 pytest 转绿（自纠到全绿）。
- 全部核心机制（工具分发 / 治理拦截 / 反馈回灌 / 记忆读写 / 停机）有 mock/stub LLM 驱动、不依赖网络的确定性单测；`make test` / CI 一键跑且 pass。
- 凭据与分发经得起"全新机器从零运行"检验。
- 冷启动陌生 agent 仅凭 SPEC + PLAN 能推进 1-2 个 task。

---

## §10 风险与未决问题

- 国内 LLM 工具调用 / function-calling 稳定性与格式差异 → 退化为自解析 JSON（ReAct 协议已为此设计）。
- 薄 Web 前端与 CLI 职责切分，避免 Web 分散深挖精力。
- Open Design 具体设计系统 / skill 套件名待接入仓库时确认（当前网络无法直达 GitHub）。
- 阿里云学生免费额度上限与成本控制。
- subagent task 颗粒度（PLAN 阶段细化）。
- mock LLM 的 ReAct 脚本如何既确定又逼真（影响演示③可信度）。

---

## §11 领域与机制设计（A.5 额外节）

- **反馈信号**：`PytestValidator`（解析 exit code + traceback）+ `ExitCodeProbe`（任意命令 exit code），独立 `Validator` 模块（非工具、非提示词）；产物 → 固定 8 类 taxonomy（按特异性高→低顺序匹配）+ 修复提示 → 回灌。
- **危险动作**：三级 `guardrail(action, project_root)`（**无状态纯函数**；致命自动阻断 / 危险 HITL / 安全放行），代码识别 + 拦截 + HITL 状态机；致命级不可配置关闭；需文件系统状态的规则（覆盖已存在文件）在分发层处理。
- **所需工具**：文件四件套 + 受限 `run_shell`；working-dir 围栏 + 危险子串黑名单。
- **记忆需求**：项目约定 / 历史决策 / 代码库约定；`.harness/*.md` 存储 + 自实现检索 + 按需注入。
- **重点维度 = 反馈闭环**，理由：coding 场景反馈最客观、最可编码；taxonomy 分类 + 自纠轮数 + 早停条件全部为确定性代码，可 mock 单测，最契 A.4-(B)(C)，演示 ②③ 天然落地。
- **机制如何编码（呼应 §A.4）**：主循环 / 工具分发 / 护栏 / 校验器 / 记忆读写 / 停机 全部自实现，可注入 mock LLM 单测；**不寄生于** LangChain `AgentExecutor`、AutoGen、CrewAI 等高层循环。配置文件、规则文件、技能 / 提示词文件为"内容物"，不计入 harness 实现工作量。
