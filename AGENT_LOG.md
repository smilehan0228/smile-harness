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
