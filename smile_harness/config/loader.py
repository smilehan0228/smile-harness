"""YAML loader with validation — 加载、校验并返回 Config 对象。"""

import yaml
from pathlib import Path

from smile_harness.config.schema import (
    Config,
    ToolConfig,
    GuardrailConfig,
    ValidatorConfig,
    LLMConfig,
)

# 致命规则 — 硬编码，不可通过配置关闭
FATAL_RULES = [
    "rm_rf",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "fork_bomb",
    "git_push_force",
    "drop_table",
    "drop_database",
    "path_traversal",
]

# 顶层必填字段
REQUIRED_FIELDS = ["tools", "guardrail_rules", "validators", "llm"]

# 字段名 → 子配置 dataclass 映射
SECTION_CLASSES: dict[str, type] = {
    "tools": ToolConfig,
    "guardrail_rules": GuardrailConfig,
    "validators": ValidatorConfig,
    "llm": LLMConfig,
}


def load_config(path: str) -> Config:
    """加载 YAML 配置文件，校验并返回 Config 对象。

    Args:
        path: YAML 配置文件路径。

    Returns:
        Config: 校验后的配置对象。

    Raises:
        FileNotFoundError: 文件不存在。
        yaml.YAMLError: YAML 语法错误（含行号信息）。
        ValueError: 必填字段缺失或致命规则被禁用。
        TypeError: 字段类型错误。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    # 解析 YAML
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        # 附加行号信息
        if hasattr(e, "problem_mark") and e.problem_mark is not None:
            mark = e.problem_mark
            msg = (
                f"YAML syntax error at line {mark.line + 1}, "
                f"column {mark.column + 1}: {e.problem}"
            )
        else:
            msg = f"YAML syntax error: {e}"
        raise yaml.YAMLError(msg) from e

    if not isinstance(data, dict):
        raise ValueError(
            f"Config file must contain a YAML mapping, "
            f"got {type(data).__name__}: {path}"
        )

    # 检查必填字段
    for field_name in REQUIRED_FIELDS:
        if field_name not in data:
            raise ValueError(
                f"Missing required field: '{field_name}' in config file {path}"
            )

    # 构建子配置
    config_kwargs: dict = {}
    for section_name, section_cls in SECTION_CLASSES.items():
        section_data = data.get(section_name)
        if section_data is None:
            section_data = {}
        if not isinstance(section_data, dict):
            raise TypeError(
                f"'{section_name}' must be a mapping, "
                f"got {type(section_data).__name__} in {path}"
            )
        config_kwargs[section_name] = section_cls(**section_data)

    # 处理 max_iters
    if "max_iters" in data:
        val = data["max_iters"]
        if isinstance(val, bool) or not isinstance(val, int):
            raise TypeError(
                f"max_iters must be an int, "
                f"got {type(val).__name__} ({val!r}) in {path}"
            )
        config_kwargs["max_iters"] = val

    # 构建 Config
    config = Config(**config_kwargs)

    # 校验致命规则不可关闭
    disabled = config.guardrail_rules.disabled_danger_rules
    for rule in disabled:
        if rule in FATAL_RULES:
            raise ValueError(
                f"Fatal rule '{rule}' cannot be disabled. "
                f"Fatal rules are: {', '.join(FATAL_RULES)}"
            )

    return config