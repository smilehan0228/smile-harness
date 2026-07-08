# PLAN.md — smile-harness 实现计划

> 由 `writing-plans` 产出。每个 task 颗粒度可由一个 subagent 在一次会话内完成。
> 纪律：TDD 先红再绿再重构；SPEC+PLAN 通过冷启动验证前不写实现代码；每 task 一个 worktree→一个 PR；完成即标记 commit hash。

## 并行波段

- **Band A（地基，串行）**：T0 → T1。所有机制依赖 LLM 抽象层 + mock。
- **Band B（核心机制，T1 后大批并行）**：T2 / T3 / T5 / T6 / T8 / T9 / T10 互不依赖。
- **Band C（集成，需 B 汇合）**：T4←T3；T7←T6,T2；T11←T1,T2,T3；T12 汇合一切。
- **Band D（前端/分发/部署）**：T13–T18 依赖 T12。
- **Band E（文档）**：T19 持续；T20 收尾。

---

## Band A — 地基

### T0 仓库骨架
- **目标**：可一键跑测试的空骨架 + CI 含 `unit-test` job。
- **涉及文件**：`pyproject.toml`、`Makefile`、`.gitlab-ci.yml`、`smile_harness/__init__.py`、`tests/__init__.py`、`tests/test_smoke.py`、`.gitignore`。（README 占位推迟到 T16）
- **实现要点**：pyproject 声明 Python≥3.11、deps（pytest, pyyaml, keyring, httpx, fastapi, uvicorn）；`make test` = `pytest -q`；CI `unit-test` job 跑 `make test`。
- **验证步骤**：`pytest -q` 退出 0（含 smoke test）。注：pytest 9 空 suite 返回 exit 5，故 T0 即加 `tests/test_smoke.py`（导入包断言版本）使 CI 从起即绿，且不掩盖回归。Windows 本地无 `make`，用 `pytest -q` 验；CI Linux 镜像有 make 跑同 recipe。
- **依赖**：无。
- ✅ **完成**：commit `4092176`（main，已推）。subagent=T0，经两阶段评审 + review-fix（补 smoke test）。

### T1 LLM 抽象层 + mock
- **目标**：可注入 mock 的 LLM 抽象，支撑后续所有机制的离线单测。
- **涉及文件**：`smile_harness/llm/base.py`、`smile_harness/llm/mock.py`。
- **实现要点**：`LLM.complete(messages, tools) → response`；`Decision`/`Action` 类型；`MockLLM` 按脚本队列返回 ReAct 帧。
- **验证步骤（失败测试先行）**：`tests/test_mock_llm.py::test_mock_llm_returns_scripted_response` —— 依次返回脚本帧、耗尽抛错。
- **依赖**：T0。
- ✅ **完成**：commit `bf9eef3`（PR #1 squash 合并 main，已推）。subagent=T1，两阶段评审通过（spec 合规+代码质量，无 Critical）。`LLM.complete(messages, tools)→str`（原始 ReAct JSON 串，不解析，解析留 T11）；`MockLLM` 耗尽抛 `StopIteration`，`script` 防御性拷贝。环境清理：卸载冷启动残留的 stale editable install。

---

## Band B — 核心机制（可并行）

### T2 工具四件套 + 分发
- **目标**：文件读写改列 + 受限 shell + 工具分发。
- **涉及文件**：`smile_harness/tools/base.py`、`fs.py`、`shell.py`、`dispatcher.py`。
- **实现要点**：`ToolResult{ok,content,error}`；`read_file/write_file/edit_file/list_dir`；`run_shell` 危险子串黑名单；`Dispatcher.dispatch(action)`；**`write_file`/`edit_file` 执行前检查目标文件是否存在，已存在则转 HITL**（承接 M4 移交的"覆盖已存在文件"规则，guardrail 纯函数不判此）。
- **验证步骤**：`test_read_nonexistent_returns_not_ok`；`test_write_then_read_roundtrip`；`test_edit_patch_applies`；`test_shell_blacklist_blocks_rm_rf`。
- **依赖**：T1。

### T3 三级护栏
- **目标**：`guardrail(action, project_root) → GuardrailVerdict` 三级分类，**无状态纯函数**。
- **涉及文件**：`smile_harness/guardrails/guardrail.py`（仅依赖 `Action` 类型）。
- **实现要点**：tier=fatal/danger/safe；`blocked=True` 表示不可自动执行（致命=拒绝/危险=转 HITL）；致命自动阻断不可覆盖；危险转 HITL；安全放行；写路径越界→fatal（用 `realpath` 防 `..` 穿越）；正则黑名单可配置但致命集不可关；未知动作/空命令→danger。**"覆盖已存在文件"不在本纯函数判定**，留到 T2 分发层（执行前检查存在性后转 HITL）。
- **验证步骤**：`test_rm_rf_is_fatal`；`test_git_push_force_is_fatal`；`test_curl_egress_is_danger`；`test_read_is_safe`；`test_write_outside_root_is_fatal`。
- **依赖**：T1（仅需 `Action` 类型）。

### T5 taxonomy 分类器
- **目标**：把校验产物归入固定 8 类并给修复提示。
- **涉及文件**：`smile_harness/feedback/taxonomy.py`。
- **实现要点**：`Taxonomy` 枚举固定 8 值（`SYNTAX_ERROR/IMPORT_ERROR/ASSERTION_FAIL/TIMEOUT/LINT_VIOLATION/PASS/RUNTIME_ERROR/UNKNOWN`）；`classify(raw_output) → (category, fix_hint)` 纯函数；**按特异性高→低顺序匹配**：`SYNTAX_ERROR→IMPORT_ERROR→ASSERTION_FAIL→TIMEOUT→LINT_VIOLATION→PASS→RUNTIME_ERROR→UNKNOWN`（避免 `RUNTIME_ERROR` 的 "Error" 子串误吞）。
- **验证步骤**：`test_assertion_traceback_classified`；`test_syntax_error_classified`；`test_timeout_classified`；`test_exit_zero_is_pass`；`test_unknown_rawPassthrough`。
- **依赖**：无（独立纯函数，零耦合）。

### T6 校验器注册表 + PytestValidator + ExitCodeProbe
- **目标**：独立 Validator 模块，解析产物→FeedbackResult。
- **涉及文件**：`smile_harness/feedback/validator.py`、`pytest_val.py`、`exitcode.py`。
- **实现要点**：`Validator` 抽象 + 注册表；`PytestValidator` 跑 pytest 解析 exit+traceback；`ExitCodeProbe` 跑任意命令取 exit code；输出 `FeedbackResult{category,message,fix_hint,raw}`。
- **验证步骤**：`test_pytest_validator_parses_assertion_fail`；`test_exitcode_probe_exit1_classified`。
- **依赖**：T5。

### T8 记忆存储 + 检索
- **目标**：跨会话 md 记忆 + 自实现检索。
- **涉及文件**：`smile_harness/memory/store.py`、`retrieve.py`。
- **实现要点**：`.harness/*.md` 读写 `MemoryEntry`；`retrieve(query, n)`=最近 N + 关键词匹配；按需注入。
- **验证步骤**：`test_write_then_retrieve_by_keyword`；`test_recent_n_ordering`；`test_no_credentials_stored`。
- **依赖**：T1。

### T9 配置 schema + YAML loader
- **目标**：声明式 YAML 约束五项。
- **涉及文件**：`smile_harness/config/schema.py`、`loader.py`、`config.yaml`。
- **实现要点**：`Config` dataclass（tools/guardrail_rules/validators/max_iters/llm）；loader 校验+报行号；致命规则不可关闭。
- **验证步骤**：`test_load_valid_yaml`；`test_invalid_yaml_raises_with_line`；`test_fatal_rules_not_disableable`。
- **依赖**：T1。

### T10 凭据管理
- **目标**：key 安全存取，不进 git/日志。
- **涉及文件**：`smile_harness/creds/keyring_store.py`、`env_store.py`、`manager.py`。
- **实现要点**：keyring→Windows Credential Manager 主；.env 兜底；隐藏录入、show 不回显、可清除。
- **验证步骤**：`test_keyring_set_get_with_fake_backend`；`test_show_does_not_echo_plaintext`；`test_clear_sets_unset`；`test_env_fallback_when_keyring_unavailable`。
- **依赖**：T1。

---

## Band C — 集成

### T4 HITL 状态机
- **目标**：danger 动作的人工审批流转。
- **涉及文件**：`smile_harness/guardrails/hitl.py`。
- **实现要点**：状态 pending→approved/denied；approved→执行；denied→跳过并回灌。
- **验证步骤**：`test_danger_pending_then_approved_executes`；`test_danger_pending_then_denied_skips`。
- **依赖**：T3。

### T7 自纠闭环
- **目标**：N 轮 + 早停 + 成功停 的反馈闭环。
- **涉及文件**：`smile_harness/feedback/loop.py`。
- **实现要点**：`run_loop(task, kernel)` 迭代至停机；停机条件=全绿成功 / 连续 2 同类早停 / N 到顶。
- **验证步骤**：`test_green_stops_success`；`test_n_cap_stops`；`test_two_same_category_early_stop`。
- **依赖**：T6、T2。

### T11 ReAct 决策解析
- **目标**：JSON→Action，malformed 可检测。
- **涉及文件**：`smile_harness/loop/decision.py`。
- **实现要点**：解析 thought/action/action_input；缺字段抛 `DecisionParseError`；`final` 标志。
- **验证步骤**：`test_parse_valid_react`；`test_missing_field_raises`；`test_final_flag_detected`。
- **依赖**：T1、T2、T3。

### T12 主循环集成
- **目标**：串起 LLM+工具+护栏+HITL+反馈+记忆+配置+停机。
- **涉及文件**：`smile_harness/loop/main_loop.py`。
- **实现要点**：`organize_context→call_llm→parse→guardrail→dispatch|hitl→validate→reinject→stop_check`。
- **验证步骤（mock LLM，对齐机制演示）**：`test_loop_blocks_fatal_action`（①）；`test_feedback_changes_next_action`（②）；`test_loop_fixes_broken_module_to_green`（③）。
- **依赖**：T11、T7、T4、T8、T9。

---

## Band D — 前端 / 分发 / 部署

### T13 机制演示
- **目标**：A.6 ①②③ 可重复脚本。
- **涉及文件**：`demo/broken_module/buggy.py`、`demo/broken_module/test_buggy.py`、`demo/demo_mechanisms.py`。
- **验证步骤**：`demo_mechanisms.py` 跑通并断言三种行为；纳入 `make demo`。
- **依赖**：T12。

### T14 CLI
- **目标**：`minicc` 命令行。
- **涉及文件**：`smile_harness/cli/app.py`。
- **实现要点**：子命令 `<task>` / `config init|edit` / `key set|show|clear`。
- **验证步骤**：`test_key_show_no_key_status`；`test_config_init_writes_yaml`；`test_cli_fix_task_mock_green`。
- **依赖**：T12、T10、T9。

### T15 薄 Web 前端
- **目标**：浏览器聊天驱动内核。
- **涉及文件**：`smile_harness/web/server.py`、`web/static/`(Open Design)。
- **实现要点**：FastAPI `/chat` 流式事件；Open Design 设计系统接入；调同一内核库。
- **验证步骤**：`test_post_chat_with_mock_kernel_streams_events`。
- **依赖**：T12。

### T16 打包分发
- **目标**：PyPI + Docker 双形态可获取运行。
- **涉及文件**：`Dockerfile`、`pyproject.toml` 补打包元数据、`README.md` 补获取/运行/key 配置/限制。
- **验证步骤**：`docker build` + `docker run --rm smile-harness --help`；`pip install -e .` 可用。
- **依赖**：T14。

### T17 CI
- **目标**：pipeline 绿、含 `unit-test` + `docker-build`。
- **涉及文件**：`.gitlab-ci.yml`。
- **验证步骤**：最后一次 CI pass；`unit-test` job 存在。
- **依赖**：T16、全部测试。

### T18 云部署
- **目标**：线上 WebUI 可访问。
- **涉及文件**：部署配置、`README.md` 部署架构节。
- **验证步骤**：公网 URL 可访问 WebUI。
- **依赖**：T15。

---

## Band E — 文档

### T19 AGENT_LOG.md
- **目标**：按时间序记录关键节点（时间戳/task/技能/prompt/commit/人工干预/教训）。全程持续更新。
- **依赖**：全程。

### T20 REFLECTION.md
- **目标**：1500–2500 字反思，本人撰写（AI 润色需标注）。
- **依赖**：收尾。

---

## 冷启动验证（实现前必做）

- **试跑 task**：T3（护栏）、T5（taxonomy）。
- **方式**：用与主开发智能体不同的 agent，全新 session、不导入会话/memory、仅给 `SPEC.md`+`PLAN.md`+该 task 说明、遇不确定即暂停询问。
- **记录**：写入 `SPEC_PROCESS.md`（受阻处、spec 缺陷、解读偏差、修订 diff）。
- **通过后**：方可进入 T0 起的实现。
