"""Config dataclass — 声明式配置模型（SPEC §3 M6）。"""

from dataclasses import dataclass, field


@dataclass
class ToolConfig:
    """工具开关配置。"""

    read_file: bool = True
    write_file: bool = True
    edit_file: bool = True
    list_dir: bool = True
    run_shell: bool = True


@dataclass
class GuardrailConfig:
    """危险规则配置。致命规则不可关闭（硬编码在 loader 中）。"""

    disabled_danger_rules: list[str] = field(default_factory=list)


@dataclass
class ValidatorConfig:
    """校验器选择配置。"""

    enabled: list[str] = field(default_factory=lambda: ["pytest", "exitcode"])


@dataclass
class LLMConfig:
    """LLM 供应商配置。"""

    provider: str = "deepseek"
    model: str = "deepseek-chat"
    endpoint: str = "https://api.deepseek.com/v1"
    temperature: float = 0.0


@dataclass
class Config:
    """顶层配置。"""

    tools: ToolConfig
    guardrail_rules: GuardrailConfig
    validators: ValidatorConfig
    llm: LLMConfig
    max_iters: int = 5