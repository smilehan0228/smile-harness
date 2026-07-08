# smile-harness

一个极简、SPEC 驱动的 Python coding agent harness，含 ReAct 主循环、护栏治理与反馈闭环。

本项目已部署到云服务器，部署地址：[http://101.37.170.172:8000/](http://101.37.170.172:8000/) ，不过，由于预算原因，我并未对服务器后端进行大模型的API配置，目前在公网上使用的是mock llm，如有测试需要，可以用南大邮箱联系我，我把API key传到服务器后端。

这并不影响你在本地使用自己的API key来使用我的agent。

这是我的AI4SE 期末项目——深入探索 coding agent 内部机制：工具分发、ReAct 决策循环、护栏拦截、多源反馈校验。

## 特性

- **ReAct Agent 主循环** — 思考 → 选择动作 → 观察反馈 → 重复
- **工具系统** — 内置工具：`read_file`、`write_file`、`edit_file`、`list_dir`、`run_shell`
- **三级护栏** — 拦截危险 shell 命令（`rm -rf`、`sudo` 等），致命/危险/安全三级分类
- **反馈闭环** — pytest 运行器、exit-code 探针、8 类 taxonomy 分类器、自纠循环
- **凭据管理** — keyring 安全存储，绝不落明文文件
- **CLI（`minicc`）** — 任务执行、配置初始化、密钥管理
- **Web 前端** — FastAPI + 极简聊天页（`/chat` 端点）
- **Mock LLM** — 脚本化 ReAct 响应，支持确定性离线测试

## 本地安装
本项目提供三种分发方式

### PyPI 安装

```bash
pip install smile-harness
```

### 源码安装（Git Clone）

```bash
git clone https://github.com/smilehan0228/smile-harness.git
cd smile-harness
pip install -e .
```

### Docker

```bash
docker build -t smile-harness .
docker run smile-harness minicc --help
```


## 快速开始
smile-harness 默认使用 DeepSeek API，也支持任意 OpenAI 兼容供应商。

### 1. 获取 API Key

在 [DeepSeek 平台](https://platform.deepseek.com/) 注册并获取 API Key。


### 2. 生成配置文件

```bash
minicc config init
```

会在当前目录生成 `config.yaml`，含合理默认值：

```yaml
tools:
  read_file: true
  write_file: true
  edit_file: true
  list_dir: true
  run_shell: true

guardrail_rules:
  disabled_danger_rules: []

validators:
  enabled:
    - pytest
    - exitcode

llm:
  provider: deepseek
  model: deepseek-v4-flash  #可以在该配置文件当中按需修改模型
  endpoint: https://api.deepseek.com/v1
  temperature: 0.0

max_iters: 5
```
如需使用其他供应商（如 OpenAI、Kimi 等），修改 `provider`、`endpoint` 和 `model` 字段即可，然后 `minicc key set {provider}_api_key` 配置对应 key。


#### 注意： 有 API key 时自动使用真实 LLM；无 key 时回退到 MockLLM 并提示警告。部署至云服务器的项目正是因为我没有配置API key，所以才使用mockllm的。
### 3.配置API key

通过 keyring 安全存储 LLM API Key：

```bash
minicc key set deepseek_api_key
# 回车之后，输入 'deepseek_api_key' 的值：[隐藏输入]
```

查看凭据状态：

```bash
minicc key show deepseek_api_key
# 凭据 'deepseek_api_key'：已设置

minicc key list
# deepseek_api_key
```

清除凭据：

```bash
minicc key clear deepseek_api_key
```

### CLI 命令参考

| 命令 | 说明 |
|---------|-------------|
| `minicc task <描述>` | 运行 coding 任务 |
| `minicc config init` | 生成默认 `config.yaml` |
| `minicc config edit` | 打印配置文件路径 |
| `minicc key set <名称>` | 安全存储凭据 |
| `minicc key show <名称>` | 查看凭据状态 |
| `minicc key list` | 列出所有已存凭据 |
| `minicc key clear <名称>` | 删除凭据 |
| `minicc --help` | 显示完整帮助 |


###  运行任务
参考上面的命令格式，我们可以运行agent。
```bash
minicc task "在项目根目录创建一个 hello.py"
```
## Web 前端服务

### 在线体验前端功能
本项目已部署至云服务器，如果需要使用自己的API key，请参考上方的配置真实LLM并本地运行

公网部署地址：**[http://101.37.170.172:8000/](http://101.37.170.172:8000/)**（未配置API key,使用mock llm代为展示前端功能）

### 本地运行
如果你不习惯CLI的模式，可以在本地环境运行前端
```bash
python -m uvicorn smile_harness.web.server:app --reload
```

然后打开 http://localhost:8000 来使用一个网页端聊天页面与agent交谈。
## 架构

```
smile_harness/
├── cli/          # minicc 命令行（argparse）
├── config/       # YAML 配置加载
├── creds/        # keyring + .env 凭据存储
├── feedback/     # pytest 运行器、exit-code 探针、taxonomy 分类器
├── guardrails/   # 危险命令检测、HITL 状态机
├── llm/          # LLM 抽象层（base + mock）
├── loop/         # ReAct 决策解析 + 主循环
├── memory/       # 内存存储 + 检索
├── tools/        # 工具分发、文件操作、shell 执行
└── web/          # FastAPI 服务 + 聊天 HTML
```

## 已知限制

- **Python 3.11+** 必须
- **真实 LLM 需自备 API Key** — 默认 DeepSeek（OpenAI 兼容协议），也支持其他兼容供应商。配置方式见下方"配置真实 LLM"。
- **无持久化状态** — 会话存于内存，无数据库或检查点。
- **单用户** — 不支持多租户或并发会话。




## 测试

### 一键运行全部测试

可一键运行所有共 183 个测试，含核心机制确定性单测（MockLLM，无需网络）：

```bash
pytest -q
```

### harness核心机制的确定性单元测试


对应 SPEC A.6 三项机制演示，全程 MockLLM，确定性复现：

| 演示 | 内容 | 测试入口 |
|------|------|----------|
| ① 护栏拦截 | `rm -rf /` → guardrail 判 fatal → blocked | `pytest tests/test_main_loop.py -k "blocks"` |
| ② 反馈闭环 | 语法错误反馈注入下一轮 → 行为改变 | `pytest tests/test_main_loop.py -k "feedback"` |
| ③ 修复到全绿 | write→pytest 失败→edit 修复→PASS | `pytest tests/test_main_loop.py -k "green"` |

也可一键运行独立演示脚本：

```bash
python demo/demo_mechanisms.py
```

## 许可证

MIT