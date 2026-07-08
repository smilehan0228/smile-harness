# REFLECTION.md — smile-harness 项目反思

> AI4SE 期末项目 A · Coding Agent Harness
> 作者：smile
> 标注：本文由本人撰写，AI 辅助润色与结构优化。

---

## 一、项目概述与初衷

smile-harness 是一个从零自研的 Python coding agent harness。目标不是做"最强 agent"，而是把 `Agent = LLM + Harness` 这层工程透明化——让学习者看清决策封装、工具、记忆、治理、反馈、配置这六层如何各司其职，且每层都能用 mock LLM 做确定性单测。

选择**反馈闭环**作为深挖维度的原因很朴素：coding 场景的反馈最客观、最可编码——pytest 的 exit code 和 traceback 不会说谎，taxonomy 分类和自纠轮数全部可以写成确定性代码，不依赖提示词工程的"玄学"。

---

## 二、工作流反思：SPEC → PLAN → TDD → subagent+worktree+PR

### 2.1 SPEC 驱动开发

这次最大的方法论收获是 **SPEC 先行的价值**。brainstorming 阶段逐块签字沉淀出 11 节 SPEC 和 20 task 的 PLAN，加上冷启动验证（用另一类型 agent 零上下文跑 T3+T5），暴露了 7 处 SPEC/PLAN 缺陷——接口签名、字段语义、依赖关系、枚举值这些"我以为写清楚了"的东西，在零上下文的陌生 agent 眼里全是歧义。

这让我深刻意识到：**弹性在 brainstorming 阶段像宽容，在实现阶段就是歧义**。如果跳过 SPEC 直接写代码，这些缺陷会散落在 20 个 task 的 172 个测试里，修复成本远高于在 SPEC 阶段纠正。

### 2.2 Subagent + Worktree + PR 流水线

20 个 task 全部由 subagent 在独立 git worktree 中完成，经 TDD（先红再绿）后 squash merge 为独立 PR。这个流水线的优势在于：

- **隔离性**：每个 task 一个 worktree，互不干扰。Band B 的 5 个 subagent 完全并行，零冲突。
- **可追溯**：每个 PR 对应一个 commit，PLAN.md 标注 commit hash，AGENT_LOG.md 记录全过程。回看时能精确知道每个模块是谁、何时、怎么写的。
- **质量门禁**：subagent 不能直接 merge，必须通过主 agent 的评审。T0 的 subagent 被发回 fix（补 smoke test）就是典型案例——subagent 的判断力可信任，但需要主 agent 复核其"拒绝"是否漏掉了正确替代方案。

教训是：**worktree 的 branch 清理很麻烦**。`gh pr merge --delete-branch` 在 worktree 仍持有分支时必然失败，需要手动 `git worktree remove` 后 `git branch -D`。这在整个项目中是反复出现的摩擦点。

### 2.3 冷启动验证

冷启动用 opencode+deepseek-v4-pro（与主方 Claude Code 不同类型）零上下文跑 T3+T5，10/10 测试通过，暴露 7 处缺陷。这个环节是 SPEC 质量的最强检验——**主 agent 自审发现不了"未明文写死的契约缺口"，因为带隐性上下文会自动脑补；冷启动的零上下文才暴露这些**。

冷启动方自创的合理决策（固定 8 类 taxonomy、特异性高→低匹配顺序、blocked 语义、未知动作→danger）被采纳进 SPEC，证明了"不同 agent 独立实现同一 SPEC"的验证价值。

---

## 三、架构反思

### 3.1 六维度设计

六维度（决策/工具/记忆/治理/反馈/配置）的划分在实现中证明是合理的。每个维度的模块边界清晰：

- **LLM 抽象层**（T1）：`LLM.complete()` 一个方法，MockLLM 按脚本队列返回——简单但够用。
- **工具四件套**（T2）：`read/write/edit/list_dir + run_shell`，`edit_file` 的 old_str/new_str 语义（恰好一次出现才替换）避免了 patch 歧义。
- **三级护栏**（T3）：`guardrail(action, project_root)` 无状态纯函数——这个设计决策来自冷启动反馈，让护栏可单测、不依赖文件系统。
- **HITL 状态机**（T4）：pending→approved/denied，终态锁死——简单但完整。
- **反馈闭环**（T5/T6/T7）：taxonomy 分类器 + 校验器注册表 + 自纠循环，三层各司其职。
- **记忆/配置/凭据**（T8/T9/T10）：三个独立模块，无互相依赖。

### 3.2 反馈闭环——深挖维度

反馈闭环是三层设计：

1. **Taxonomy 分类器**（T5）：纯函数，8 类枚举，按特异性高→低匹配。`SYNTAX_ERROR` 先于 `RUNTIME_ERROR` 匹配，避免 "Error" 子串误吞。
2. **校验器注册表**（T6）：`PytestValidator` 解析 exit code + traceback，`ExitCodeProbe` 取任意命令 exit code。注册表可插拔。
3. **自纠循环**（T7）：N 轮上限 + 连续 2 轮同类早停 + 全绿成功停。纯状态管理器，不依赖 LLM。

这个设计在 T12 主循环集成中验证了——三项机制演示（护栏拦截→反馈注入→修复到全绿）全部通过 MockLLM 确定性复现。

### 3.3 做对了什么

- **mock 优先**：所有核心机制都有 mock 单测。172 个测试在 20 秒内跑完，不需要网络、不需要真实 LLM。这是 A.4-C 的硬标准。
- **纯函数优先**：guardrail、taxonomy、FeedbackLoop 都是纯函数/纯状态机，不访问文件系统、不依赖外部服务，单测零成本。
- **不寄生于框架**：主循环/工具分发/护栏/校验器全部自实现，不依赖 LangChain AgentExecutor 等高层循环。这满足了 A.4-B。

### 3.4 可以做得更好的

- **T13 的 commit message 异常**：subagent 在 PR body 中用了 `@` 字符导致 GitHub 截断标题。应该在 subagent prompt 中明确约束 PR 格式。
- **T16/T18 Dockerfile 冲突**：两个 task 都创建 Dockerfile，但 PLAN 未标注冲突。T18 依赖 T15 而非 T16，导致并行开发时合并冲突。应该在 PLAN 中标注共享文件。
- **真实 LLM 集成**：项目目前只实现了 MockLLM。虽然抽象层设计支持真实 LLM 注入，但缺少 DeepSeek 适配器。这是时间约束下的妥协。
- **前端太薄**：T15 的 Web 前端是极简聊天页，没有流式事件、没有会话管理。Open Design 设计系统也因网络限制未能接入。
- **Worktree 残留**：项目中积累了 14 个 worktree 目录，应定期清理。

---

## 四、AI 辅助开发的反思

这个项目本身就是一个元实验：**用 AI（Claude Code）来构建一个 AI coding agent harness**。

### 4.1 AI 擅长的

- **规格到代码的翻译**：给 subagent 一份 SPEC + PLAN + task 说明，它能产出符合规格的代码 + 测试。TDD 纪律（先红再绿）由 subagent 自主执行，成功率很高。
- **并行化**：Band B 的 5 个 subagent 同时启动，20 分钟内完成 5 个独立模块——人工不可能做到这个速度。
- **测试生成**：172 个测试覆盖了所有模块的边界条件，subagent 在写测试时展现出了较好的边界意识。

### 4.2 AI 不擅长的

- **跨 task 的全局一致性**：T16 和 T18 的 Dockerfile 冲突就是典型——两个 subagent 各自独立工作，不知道对方也在创建同名文件。
- **commit message 质量**：T13 的 "@" 异常说明 subagent 对 PR 工具的使用细节不够谨慎。
- **设计决策**：冷启动暴露的 7 处 SPEC 缺陷中，大部分是接口签名和语义歧义——这些恰恰是 AI 在"脑补"隐性上下文时容易忽略的。

### 4.3 人的角色

在这个工作流中，人的角色从"写代码"变成了"写规格 + 评审 + 集成"：
- **写 SPEC/PLAN**：定义做什么、怎么做、边界在哪——这是最需要人类判断力的环节。
- **评审 subagent 产出**：不是审代码风格，而是审"是否偏离了 SPEC 的意图"。
- **处理冲突**：T18 的 rebase 冲突需要人判断"保留哪个 Dockerfile、如何适配测试"——这是跨 task 的全局决策。

---

## 五、总结

smile-harness 是一个 20 task、172 测试、全部由 subagent 驱动的项目。它证明了：**一个好的 SPEC + 严格的 TDD 纪律 + 合理的并行波段设计，可以让 AI 高效地完成一个中等复杂度的软件项目**。

但更重要的是，它让我理解了 coding agent harness 的内部工程——不是魔法，而是决策封装、工具分发、护栏治理、反馈闭环、记忆管理、配置声明这六层确定性的代码。每一层都可以被读、被改、被 mock 单测，这正是"透明化"的意义。

**最终交付**：172 个测试全绿，六维度各有可运行实现，反馈闭环（深挖维度）有完整的 taxonomy + 自纠 + 早停，三项机制演示通过 MockLLM 确定性复现，Docker + PyPI 双形态可分发，CI/CD pipeline 就绪。

感谢 AI4SE 课程提供的探索空间，以及 Claude Code 在这个元实验中的"双重身份"——既是工具，也是研究对象。