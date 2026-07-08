"""T6: 校验器注册表 + PytestValidator + ExitCodeProbe 测试"""

import sys
import pytest
from smile_harness.feedback.taxonomy import Taxonomy
from smile_harness.feedback.validator import FeedbackResult, Validator, ValidatorRegistry
from smile_harness.feedback.pytest_val import PytestValidator
from smile_harness.feedback.exitcode import ExitCodeProbe


class TestPytestValidator:
    def test_pytest_validator_parses_assertion_fail(self, tmp_path):
        """用 pytest 跑一个含 assert 失败的测试文件，返回 ASSERTION_FAIL"""
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("def test_fail():\n    assert 1 == 2\n")

        validator = PytestValidator()
        result = validator.validate(str(test_file))

        assert result.category == Taxonomy.ASSERTION_FAIL
        assert "assert" in result.raw.lower() or "AssertionError" in result.raw
        assert len(result.fix_hint) > 0
        assert isinstance(result.message, str) and len(result.message) > 0

    def test_pytest_validator_parses_pass(self, tmp_path):
        """用 pytest 跑一个通过的测试，返回 PASS"""
        test_file = tmp_path / "test_pass.py"
        test_file.write_text("def test_pass():\n    assert 1 == 1\n")

        validator = PytestValidator()
        result = validator.validate(str(test_file))

        assert result.category == Taxonomy.PASS
        assert len(result.fix_hint) > 0
        assert isinstance(result.message, str) and len(result.message) > 0


class TestExitCodeProbe:
    def test_exitcode_probe_exit1_classified(self):
        """运行 python -c \"exit(1)\" 返回非 PASS"""
        probe = ExitCodeProbe()
        result = probe.validate(f'{sys.executable} -c "exit(1)"')

        assert result.category != Taxonomy.PASS
        assert len(result.fix_hint) > 0
        assert isinstance(result.message, str) and len(result.message) > 0

    def test_exitcode_probe_exit0_classified(self):
        """运行 echo hello 返回 PASS"""
        probe = ExitCodeProbe()
        result = probe.validate("echo hello")

        assert result.category == Taxonomy.PASS
        assert len(result.fix_hint) > 0
        assert isinstance(result.message, str) and len(result.message) > 0


class TestValidatorRegistry:
    def test_validator_registry_register_and_get(self):
        """注册校验器后能正确获取"""
        registry = ValidatorRegistry()
        probe = ExitCodeProbe()
        registry.register("exitcode", probe)

        retrieved = registry.get("exitcode")
        assert retrieved is probe

    def test_validator_registry_get_nonexistent(self):
        """获取不存在的校验器返回 None"""
        registry = ValidatorRegistry()
        assert registry.get("nonexistent") is None

    def test_validator_registry_list_names(self):
        """列出所有已注册校验器名"""
        registry = ValidatorRegistry()
        registry.register("a", ExitCodeProbe())
        registry.register("b", PytestValidator())

        names = registry.list_names()
        assert "a" in names
        assert "b" in names
        assert len(names) == 2

    def test_validator_registry_validate(self):
        """通过注册表调用校验器"""
        registry = ValidatorRegistry()
        registry.register("exitcode", ExitCodeProbe())

        result = registry.validate("exitcode", "echo hello")
        assert result.category == Taxonomy.PASS
        assert isinstance(result, FeedbackResult)


def test_feedback_result_fields():
    """FeedbackResult 数据类字段正确"""
    result = FeedbackResult(
        category=Taxonomy.PASS,
        message="All good",
        fix_hint="No fix needed",
        raw="OK",
    )
    assert result.category == Taxonomy.PASS
    assert result.message == "All good"
    assert result.fix_hint == "No fix needed"
    assert result.raw == "OK"