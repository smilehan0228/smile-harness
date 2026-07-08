"""T5: taxonomy 分类器 — 把校验产物归入固定 8 类并给修复提示"""

from enum import Enum


class Taxonomy(Enum):
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    ASSERTION_FAIL = "assertion_fail"
    TIMEOUT = "timeout"
    LINT_VIOLATION = "lint_violation"
    PASS = "pass"
    RUNTIME_ERROR = "runtime_error"
    UNKNOWN = "unknown"


# 分类规则按特异性从高到低排列，先匹配先返回
_RULES: list[tuple[Taxonomy, str, str]] = [
    (
        Taxonomy.SYNTAX_ERROR,
        "SyntaxError|IndentationError|invalid syntax",
        "Check for syntax errors: missing colons, brackets, or indentation",
    ),
    (
        Taxonomy.IMPORT_ERROR,
        "ImportError|ModuleNotFoundError|No module named",
        "Install missing package or check module path",
    ),
    (
        Taxonomy.ASSERTION_FAIL,
        "AssertionError|assert",
        "Check expected vs actual values in the assertion",
    ),
    (
        Taxonomy.TIMEOUT,
        "timeout|timed out|TimeoutExpired",
        "Operation took too long — consider increasing timeout or optimizing the code",
    ),
    (
        Taxonomy.LINT_VIOLATION,
        r"\b[EW]\d{3}\b|pylint|flake8|mypy",
        "Fix linting issues: check line length, naming, type annotations, or formatting",
    ),
    (
        Taxonomy.PASS,
        "",  # special-cased: exit_code == 0 and no error markers
        "All checks passed",
    ),
    (
        Taxonomy.RUNTIME_ERROR,
        "Error|Exception|Traceback|raise|FAILED",
        "A runtime error occurred — check the traceback for details",
    ),
    (
        Taxonomy.UNKNOWN,
        "",  # fallback — always matches
        "Unable to classify the output automatically",
    ),
]


def classify(raw_output: str, exit_code: int | None = None) -> tuple[Taxonomy, str]:
    """返回 (category, fix_hint)。规则按特异性从高到低，先匹配先返回。"""
    import re

    # PASS: exit_code == 0 且无错误痕迹
    error_markers = re.compile(
        r"Error|Exception|Traceback|FAILED|SyntaxError|IndentationError|"
        r"ImportError|ModuleNotFoundError|AssertionError|timeout|timed out|"
        r"TimeoutExpired", re.IGNORECASE
    )
    if exit_code == 0 and not error_markers.search(raw_output):
        return Taxonomy.PASS, "All checks passed"

    for taxonomy, pattern, hint in _RULES:
        if taxonomy == Taxonomy.PASS or taxonomy == Taxonomy.UNKNOWN:
            continue  # handled separately
        if pattern and re.search(pattern, raw_output, re.IGNORECASE):
            return taxonomy, hint

    return Taxonomy.UNKNOWN, "Unable to classify the output automatically"