"""T5: taxonomy 分类器 测试"""

import pytest
from smile_harness.feedback.taxonomy import Taxonomy, classify


def test_syntax_error_classified():
    """含 SyntaxError 的输出 → SYNTAX_ERROR"""
    output = 'Traceback (most recent call last):\n  File "test.py", line 1\nSyntaxError: invalid syntax'
    category, hint = classify(output, exit_code=1)
    assert category == Taxonomy.SYNTAX_ERROR
    assert isinstance(hint, str) and len(hint) > 0


def test_import_error_classified():
    """含 ModuleNotFoundError → IMPORT_ERROR"""
    output = 'ModuleNotFoundError: No module named \'requests\''
    category, hint = classify(output, exit_code=1)
    assert category == Taxonomy.IMPORT_ERROR
    assert isinstance(hint, str) and len(hint) > 0


def test_assertion_traceback_classified():
    """含 AssertionError → ASSERTION_FAIL"""
    output = 'AssertionError: assert 2 == 3'
    category, hint = classify(output, exit_code=1)
    assert category == Taxonomy.ASSERTION_FAIL
    assert isinstance(hint, str) and len(hint) > 0


def test_timeout_classified():
    """含 timed out → TIMEOUT"""
    output = 'subprocess.CalledProcessError: Command timed out after 30 seconds'
    category, hint = classify(output, exit_code=1)
    assert category == Taxonomy.TIMEOUT
    assert isinstance(hint, str) and len(hint) > 0


def test_lint_violation_classified():
    """含 E501 → LINT_VIOLATION"""
    output = 'test.py:1:80: E501 line too long'
    category, hint = classify(output, exit_code=1)
    assert category == Taxonomy.LINT_VIOLATION
    assert isinstance(hint, str) and len(hint) > 0


def test_exit_zero_is_pass():
    """exit_code=0, 无错误 → PASS"""
    output = 'All tests passed!\nOK'
    category, hint = classify(output, exit_code=0)
    assert category == Taxonomy.PASS
    assert isinstance(hint, str) and len(hint) > 0


def test_runtime_error_classified():
    """含 RuntimeError 但无更特异匹配 → RUNTIME_ERROR"""
    output = 'RuntimeError: something went wrong'
    category, hint = classify(output, exit_code=1)
    assert category == Taxonomy.RUNTIME_ERROR
    assert isinstance(hint, str) and len(hint) > 0


def test_unknown_raw_passthrough():
    """无意义字符串 → UNKNOWN"""
    output = 'some random gibberish output'
    category, hint = classify(output, exit_code=None)
    assert category == Taxonomy.UNKNOWN
    assert isinstance(hint, str) and len(hint) > 0


def test_specificity_order():
    """同时含 SyntaxError 和 Error → SYNTAX_ERROR（非 RUNTIME_ERROR）"""
    output = 'SyntaxError: invalid syntax\nError: something failed'
    category, hint = classify(output, exit_code=1)
    assert category == Taxonomy.SYNTAX_ERROR
    assert category != Taxonomy.RUNTIME_ERROR