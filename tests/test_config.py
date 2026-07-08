"""T9 配置模块测试 — config schema + YAML loader 校验。"""

import pytest

from smile_harness.config.loader import load_config
from smile_harness.config.schema import Config


class TestLoadValidYAML:
    """合法 YAML 应生成正确的 Config 对象。"""

    def test_load_valid_yaml(self, tmp_path):
        yaml_content = """\
tools:
  read_file: true
  write_file: true
guardrail_rules:
  disabled_danger_rules: []
validators:
  enabled: ["pytest", "exitcode"]
llm:
  provider: "deepseek"
  model: "deepseek-chat"
max_iters: 5
"""
        path = tmp_path / "config.yaml"
        path.write_text(yaml_content)

        config = load_config(str(path))
        assert isinstance(config, Config)
        assert config.tools.read_file is True
        assert config.tools.write_file is True
        assert config.llm.provider == "deepseek"
        assert config.llm.model == "deepseek-chat"
        assert config.max_iters == 5


class TestInvalidYAML:
    """YAML 语法错误应报错并包含行号信息。"""

    def test_invalid_yaml_raises_with_line(self, tmp_path):
        yaml_content = """\
tools:
  read_file: true
  - invalid_list_item: oops
"""
        path = tmp_path / "config.yaml"
        path.write_text(yaml_content)

        with pytest.raises(Exception) as exc_info:
            load_config(str(path))
        err_msg = str(exc_info.value).lower()
        # YAMLError 应包含行号信息
        assert "line" in err_msg or "syntax" in err_msg


class TestFatalRules:
    """致命规则不可通过 disabled_danger_rules 关闭。"""

    def test_fatal_rules_not_disableable(self, tmp_path):
        yaml_content = """\
tools:
  read_file: true
guardrail_rules:
  disabled_danger_rules: ["rm_rf", "shutdown"]
validators:
  enabled: ["pytest"]
llm:
  provider: "deepseek"
max_iters: 5
"""
        path = tmp_path / "config.yaml"
        path.write_text(yaml_content)

        with pytest.raises(ValueError, match="rm_rf"):
            load_config(str(path))


class TestMissingField:
    """缺少必填字段应报错。"""

    def test_missing_required_field_raises(self, tmp_path):
        yaml_content = """\
tools:
  read_file: true
guardrail_rules:
  disabled_danger_rules: []
validators:
  enabled: ["pytest"]
"""
        path = tmp_path / "config.yaml"
        path.write_text(yaml_content)

        with pytest.raises(ValueError, match="llm"):
            load_config(str(path))


class TestTypeError:
    """类型错误（如 max_iters 为字符串）应报错。"""

    def test_type_error_raises(self, tmp_path):
        yaml_content = """\
tools:
  read_file: true
guardrail_rules:
  disabled_danger_rules: []
validators:
  enabled: ["pytest"]
llm:
  provider: "deepseek"
max_iters: "not_a_number"
"""
        path = tmp_path / "config.yaml"
        path.write_text(yaml_content)

        with pytest.raises((TypeError, ValueError), match="max_iters"):
            load_config(str(path))


class TestDefaults:
    """最小 YAML（仅必填字段）→ 默认值应生效。"""

    def test_default_values_applied(self, tmp_path):
        yaml_content = """\
tools:
  read_file: true
guardrail_rules: {}
validators: {}
llm: {}
"""
        path = tmp_path / "config.yaml"
        path.write_text(yaml_content)

        config = load_config(str(path))
        assert config.max_iters == 5
        assert config.tools.read_file is True
        assert config.tools.write_file is True
        assert config.tools.edit_file is True
        assert config.tools.list_dir is True
        assert config.tools.run_shell is True
        assert config.llm.provider == "deepseek"
        assert config.llm.model == "deepseek-chat"
        assert config.llm.endpoint == "https://api.deepseek.com/v1"
        assert config.llm.temperature == 0.0
        assert config.validators.enabled == ["pytest", "exitcode"]
        assert config.guardrail_rules.disabled_danger_rules == []