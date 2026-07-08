# smile-harness

A minimal, spec-driven Python coding-agent harness with ReAct loop, guardrails, and feedback validation.

Built for the AI4SE final project — a hands-on exploration of coding-agent internals: tool dispatch, ReAct decision loops, guardrail enforcement, and multi-source feedback validation.

## Features

- **ReAct Agent Loop** — think, choose an action, observe feedback, repeat
- **Tool System** — built-in tools: `read_file`, `write_file`, `edit_file`, `list_dir`, `run_shell`
- **Guardrails** — block dangerous shell commands (`rm -rf`, `sudo`, etc.)
- **Feedback Pipeline** — pytest runner, exit-code validator, taxonomy classifier
- **Credential Management** — keyring-backed, never in plaintext files
- **CLI (`minicc`)** — task runner, config init, key management
- **Web Frontend** — FastAPI + HTML chat page (`/chat` endpoint)
- **Mock LLM** — scripted ReAct responses for deterministic testing

## Installation

### From PyPI (planned)

```bash
pip install smile-harness
```

### From source (editable)

```bash
git clone https://github.com/example/smile-harness
cd smile-harness
pip install -e .
```

### Docker

```bash
docker build -t smile-harness .
docker run smile-harness minicc --help
```

## Quick Start

### Run a coding task

```bash
minicc task "fix the bug in utils.py"
```

### Initialize config

```bash
minicc config init
```

This creates a `config.yaml` in the current directory with sensible defaults:

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
  model: deepseek-chat
  endpoint: https://api.deepseek.com/v1
  temperature: 0.0

max_iters: 5
```

### Configure credentials

Set your LLM API key securely via keyring:

```bash
minicc key set deepseek_api_key
# Enter value for 'deepseek_api_key': [hidden input]
```

Check credential status:

```bash
minicc key show deepseek_api_key
# Credential 'deepseek_api_key': 已设置

minicc key list
# deepseek_api_key
```

Clear a credential:

```bash
minicc key clear deepseek_api_key
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `minicc task <desc>` | Run a coding task with the agent loop |
| `minicc config init` | Generate default `config.yaml` |
| `minicc config edit` | Print the config file path |
| `minicc key set <name>` | Securely store a credential |
| `minicc key show <name>` | Check credential status |
| `minicc key list` | List all stored credentials |
| `minicc key clear <name>` | Remove a credential |
| `minicc --help` | Show full help |

## Architecture

```
smile_harness/
├── cli/          # minicc CLI (argparse)
├── config/       # YAML config loading
├── creds/        # keyring + env credential store
├── feedback/     # pytest runner, exitcode, taxonomy
├── guardrails/   # dangerous command detection, HITL
├── llm/          # LLM abstraction (base + mock)
├── loop/         # ReAct decision + main loop
├── memory/       # in-memory storage + retrieval
├── tools/        # dispatcher, fs, shell tools
└── web/          # FastAPI server + chat HTML
```

## Known Limitations

- **Python 3.11+** required
- **Mock LLM only** — the harness currently uses `MockLLM` with scripted responses. Real LLM integration requires a user-provided API key and a provider adapter (T2 milestone).
- **No persistent state** — sessions are in-memory; no database or checkpointing.
- **Single-user** — no multi-tenancy or concurrent sessions.

## Development

### Setup

```bash
pip install -e .
```

### Run tests

```bash
pytest -q
```

### Run the web server

```bash
python -m uvicorn smile_harness.web.server:app --reload
```

Then open http://localhost:8000 to see the chat page.

### Run the demo

```bash
python demo/demo_mechanisms.py
```

## License

MIT