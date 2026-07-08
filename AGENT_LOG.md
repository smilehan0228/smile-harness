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
