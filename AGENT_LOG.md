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
