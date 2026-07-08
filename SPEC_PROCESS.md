# SPEC_PROCESS.md — smile-harness

> 记录与 Superpowers 协作生成 SPEC 与 PLAN 的全过程。冷启动节为最关键的客观证据，待冷启动完成后补全。

---

## 一、brainstorming 关键节点

主 agent（Claude Code + glm-5.2）驱动 `brainstorming`，分四批提问、逐块签字沉淀。下列是智能体追问中**改变了设计走向**的好问题：

1. **"深挖哪个维度？"** —— 直接对应 A.4-D 的"主角维度做深"。用户原构想六维度并列，经追问锁定**反馈闭环**为深挖点（coding 反馈最客观、最可 mock 单测）。
2. **"WebUI 与 CLI 怎么调和？"** —— 暴露了通用交付 #9（线上 WebUI 必须）与 coding harness 天然 CLI 之间的张力，这是用户原构想未涉及的。促成了"内核为库 + CLI + 薄 Web 前端"的架构定调。
3. **"危险动作护栏怎么分级？"** —— 把"治理"从模糊要求落到三级状态机（致命/危险/安全），并明确致命级不可配置关闭。
4. **"自纠闭环的停机条件？"** —— 把反馈闭环从"会自纠"细化到"N 轮 + 连续 2 同类早停 + 全绿成功停"三条**可确定性单测**的停机条件，直接服务 A.4-C。
5. **"冷启动用哪个 agent？类型是否不同？"** —— 智能体主动指出 §4.5"类型必须不同"的合规风险，促成冷启动方从"同 harness 换模型"改为"换不同类型 CLI agent"。

## 二、≥3 轮关键迭代与处理决策

### 迭代 1：架构形态（WebUI 张力）
- **背景**：用户初始构想是"对标 Claude Code 的简化 CLI harness"，未提 WebUI。
- **智能体追问**：通用交付 #9 要求线上 WebUI，与 CLI 形态冲突，如何调和？
- **处理决策**：选"内核为库 + CLI + 薄 Web 前端"。内核仍是主要贡献，Web 仅是很薄的一层，不稀释深挖精力。
- **修正了原设想**：是。原构想隐含纯 CLI，现增加薄 Web 前端与云部署。

### 迭代 2：前端是否用 Open Design
- **背景**：§3.4 说纯 CLI 可豁免 Open Design。
- **智能体追问**：薄 Web 是申请豁免，还是声明用某设计系统？
- **处理决策**：用户选**用 Open Design，不豁免**。
- **修正了原设想**：是。增加前端设计系统选型义务（具体套件名待接入仓库确认，记入 §10 风险）。

### 迭代 3：冷启动合规方
- **背景**：用户原拟冷启动 = Claude Code + deepseek-v4-pro（同 harness 换模型）。
- **智能体追问**：§4.5 要求"类型必须不同"，同 harness 有合规风险。
- **处理决策**：改为"换一个不同类型 CLI agent"（Codex/Cursor/Gemini/Copilot 任一），全新 session、不导 memory、仅给 SPEC+PLAN。
- **修正了原设想**：是。由"换模型"升级为"换 harness 类型"。

### 迭代 4（次级）：动作协议
- **背景**：动作协议未问即拟 ReAct 风格 JSON tool-call。
- **处理决策**：用户确认采纳。
- **采纳理由**：不依赖供应商私有 function-calling，便于跨供应商与 mock，契合 A.4-C 的离线可测。

## 三、AI 提出而采纳 / 推翻或修正

**采纳的 AI 建议**：
- 深挖维度选反馈闭环（AI 推荐，用户采纳）。
- 内核为库 + CLI + 薄 Web 前端（AI 推荐，用户采纳）。
- 三级护栏、N+早停+成功停、YAML 五项可配、keyring 为主 + .env 兜底、PyPI+Docker 双形态、阿里云部署（均 AI 推荐，用户采纳）。
- 动作协议 ReAct JSON（AI 拟，用户确认）。

**推翻或修正**：
- 项目工作名：AI 拟 `minicc`，用户改为 `smile-harness`。
- 前端：AI 倾向可豁免，用户决定不豁免、用 Open Design。
- 冷启动方：AI 顺承用户原意"换模型"，经合规追问后修正为"换类型"。

**为什么**：AI 的推荐多在工程稳健与合规边界上（深挖点、护栏分级、凭据、分发）；用户的推翻多在个人取向与命名（项目名、是否走 Open Design）。体现了"AI 守工程纪律、人定方向"的分工。

## 四、反思：brainstorming 技能在本项目的表现

**做得好**：
- 把 A 文件的"机制必须是代码"等硬要求转译成可签字的具体决策（如停机条件三条、护栏三级）。
- 主动暴露跨章节张力（WebUI vs CLI、冷启动类型合规），而非顺承用户原意。
- 每批问完即汇总，避免上下文发散。

**让我不满**：
- brainstorming 高度依赖问-答节奏，四批 16 问仍可能漏掉隐性假设（如 Open Design 具体套件名因网络受限未能定）。
- 对"机制可单测"的判据在追问中靠人脑保持，未对每个决策逐条标注其 mock 单测形态。
- 网络受限（GitHub 不可达）使部分选型（Open Design 套件）只能留为未决，削弱了 SPEC 的确定性。

## 五、冷启动验证（最关键的客观证据）

**执行**：冷启动方 = **opencode + deepseek-v4-pro**（与主开发方 Claude Code 不同类型，合规 §4.5）。全新 session、不导 memory、仅给 `SPEC.md`+`PLAN.md`+`COLDSTART_PROMPT.md`，跑 T3→T5。产出存于 `E:\agent\coldStart\`，自报见 `COLD_START_REPORT.md`/`IMPLEMENTATION_SUMMARY.md`。主 agent 已读其全部源码核对，自报属实。

**结果**：10/10 测试通过（TDD 红→绿→重构规范），代码质量好。但暴露 7 处 SPEC/PLAN 缺陷：

| # | 受阻/提问处 | 缺陷 | 是 spec 写错还是它读错？ | 修订 |
|---|---|---|---|---|
| 1 | "覆盖已存在文件=danger" 需文件系统状态，纯 guardrail 判不了 | SPEC §3 M4 把需 fs 状态的规则塞进纯 guardrail | **spec 写错**（职责越界） | guardrail 定为无状态纯函数；覆盖检查移到分发层 M2/T2 |
| 2 | `blocked` 在 danger 级语义未定义 | SPEC §6 字段语义缺 | **spec 写错** | 定义 `blocked=True`=不可自动执行（致命=拒绝/危险=转HITL），`tier` 区分 |
| 3 | taxonomy 匹配顺序未指定，"Error" 子串会误吞 SyntaxError | SPEC §3 M5 缺顺序 | **spec 写错** | 锁定特异性高→低顺序 |
| 4 | guardrail 的 `project_root` 参数 PLAN 未写，从测试反推 | PLAN T3 接口不全 | **spec 写错** | PLAN T3 补签名 `guardrail(action, project_root)` |
| 5 | T5 假依赖 T1（实为纯函数零耦合） | PLAN T5 依赖错 | **spec 写错** | T5 依赖改"无" |
| 6 | PLAN 未区分真实/形式依赖 | PLAN 依赖标注粗 | **spec 写错** | T3 标"仅需 Action"，T5 标"零耦合" |
| 7 | taxonomy 6-8 类未锁定名称 | SPEC 给范围未锁定 | **spec 写错**（故意留弹性反成歧义） | 锁定 8 类固定名 |

**它做出的与原意不一致的解读（均为合理，已采纳）**：
- 选 8 类（非 6/7）；匹配顺序特异性高→低；`blocked=True` for danger；guardrail 设为无状态；加 `project_root` 参数；未知动作/空命令→danger。这些 SPEC 原未写死，它的选择合理，主 agent **采纳**进 SPEC。

**产出与预期差距**：差距小——它正确实现 T3/T5 并通过测试，且主动暴露了 7 处真缺陷。差距主要在 SPEC 表达而非它的能力。这反证：SPEC 的"机制设计"方向对，但"接口签名/字段语义/依赖标注"等工程契约处仍不够精确，正是冷启动要暴露的。

**关键修订 diff（修订前→后）**：
- SPEC §3 M4：`guardrail(action) → ...` → `guardrail(action, project_root) → ...`，**无状态纯函数**；"覆盖已存在文件"从 M4 移至 M2 分发层。
- SPEC §3 M5：`6-8 类 taxonomy` → `固定 8 类 + 锁定匹配顺序`。
- SPEC §6：`GuardrailVerdict.blocked` 补语义；新增 `Taxonomy` 枚举固定 8 值条目。
- SPEC §11：反馈信号/危险动作两行对齐上述。
- PLAN T2：补"write/edit 执行前检查存在性→转 HITL"。
- PLAN T3：签名补 `project_root`；标"无状态纯函数"+"仅需 Action"。
- PLAN T5：依赖 `T1` → `无`；补匹配顺序。

**反思**：冷启动价值兑现——7 处缺陷里 6 处是"spec 写错"（接口/字段/依赖/锁定），仅靠主 agent 自审发现不了，因为主 agent 带着 brainstorming 的隐性上下文读 SPEC，会自动脑补缺口。换一个零上下文的 agent，每个未明文写死的契约处都会卡住。这正验证了 §4.5"你会严重高估 spec 清晰度"的论断。教训：**接口签名、字段语义、依赖关系、枚举值必须在 SPEC/PLAN 写死，不能留弹性**——弹性在 brainstorming 看似宽容，在实现处就是歧义。
