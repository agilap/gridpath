from __future__ import annotations

import re
from datetime import datetime

from app.models.commit import ASTSignals, CommitLabel, CommitRecord

# --- Commit message patterns --------------------------------------------------

FEATURE_PATTERN      = re.compile(r"^feat(\(.+\))?:|added?|implement|introduce|new feature|create", re.IGNORECASE)
BUGFIX_PATTERN       = re.compile(r"^fix(\(.+\))?:|bug|resolve|patch|hotfix|regression|crash", re.IGNORECASE)
REFACTOR_PATTERN     = re.compile(r"^refactor(\(.+\))?:|clean|simplif|restructur|reorganiz|deduplicate", re.IGNORECASE)
TEST_PATTERN         = re.compile(r"^test(\(.+\))?:|spec|unittest|coverage|assert|mock", re.IGNORECASE)
DOCS_PATTERN         = re.compile(r"^docs(\(.+\))?:|readme|comment|docstring|changelog|license", re.IGNORECASE)
CHORE_PATTERN        = re.compile(r"^chore(\(.+\))?:|bump|upgrade|version|ci|build|lint|format", re.IGNORECASE)
ARCHITECTURE_PATTERN = re.compile(r"arch|redesign|migrate|overhaul|scaffold|initial commit", re.IGNORECASE)

PATTERN_ORDER: list[tuple[CommitLabel, re.Pattern[str]]] = [
    ("FEATURE",      FEATURE_PATTERN),
    ("BUGFIX",       BUGFIX_PATTERN),
    ("REFACTOR",     REFACTOR_PATTERN),
    ("TEST",         TEST_PATTERN),
    ("DOCS",         DOCS_PATTERN),
    ("CHORE",        CHORE_PATTERN),
    ("ARCHITECTURE", ARCHITECTURE_PATTERN),
]

# --- Test-file detection (match on file paths, not raw diff content) ----------
# Matches `+++ b/<path>` where the file name indicates a test.
_TEST_FILE_RE = re.compile(
    r"^\+\+\+ b/(?:.*/)?(?:test_[^/\n]+|[^/\n]+_test\.py|[^/\n]+\.(?:test|spec)\.[a-z]+)$",
    re.MULTILINE,
)
# Matches files inside a tests/ or __tests__/ directory.
_TEST_DIR_RE = re.compile(r"^\+\+\+ b/(?:tests?|__tests?__)/[^\n]+$", re.MULTILINE)

# --- Diff-line heuristics (replaces broken AST reconstruction) ----------------
# These patterns match definition lines in added/removed diff lines.
_FN_RE     = re.compile(r"^\s*(?:(?:async\s+)?def |function |(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\()\w*")
_CLASS_RE  = re.compile(r"^\s*class \w")
_IMPORT_RE = re.compile(r"^\s*(?:import |from \w[\w.]*\s+import|require\s*\(|const\s+\w+\s*=\s*require)")


def _analyze_diff(diff: str) -> ASTSignals:
    """Extract structural signals directly from diff text.

    Counts definition-like lines added/removed rather than trying to
    reconstruct valid Python source from diff fragments (which fails on
    partial hunks without context lines).
    """
    added:   list[str] = []
    removed: list[str] = []

    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])

    fn_added    = sum(1 for l in added   if _FN_RE.match(l))
    fn_removed  = sum(1 for l in removed if _FN_RE.match(l))
    cls_added   = sum(1 for l in added   if _CLASS_RE.match(l))
    cls_removed = sum(1 for l in removed if _CLASS_RE.match(l))
    import_churn = sum(1 for l in added + removed if _IMPORT_RE.match(l))

    new_files     = len(re.findall(r"^new file mode",     diff, re.MULTILINE))
    deleted_files = len(re.findall(r"^deleted file mode", diff, re.MULTILINE))

    return ASTSignals(
        fn_delta=fn_added - fn_removed,
        class_delta=cls_added - cls_removed,
        # Use fn additions as a complexity proxy (no full AST available).
        complexity_delta=float(fn_added * 2),
        import_churn=import_churn,
        file_count_delta=new_files - deleted_files,
    )


# --- Message pass -------------------------------------------------------------

def _message_pass(message: str) -> tuple[CommitLabel, float]:
    for label, pattern in PATTERN_ORDER:
        match = pattern.search(message)
        if not match:
            continue
        confidence = 0.9 if match.start() == 0 else 0.7
        return label, confidence
    return "CHORE", 0.3


# --- Public classifier --------------------------------------------------------

def classify_commit(
    sha: str,
    message: str,
    diff: str,
    repo: str,
    date: datetime,
    lines_added: int,
    lines_deleted: int,
) -> CommitRecord:
    label, confidence = _message_pass(message)
    ast_signals = _analyze_diff(diff)

    if ast_signals.fn_delta >= 5 and ast_signals.complexity_delta >= 10:
        label = "ARCHITECTURE"
        confidence = 0.85

    if ast_signals.fn_delta < 0 and lines_added < lines_deleted:
        label = "REFACTOR"
        confidence = 0.9

    # Match test files by path in the diff header, not by substring in code.
    # This avoids false positives on identifiers like `latest_`, `greatest_`.
    if _TEST_FILE_RE.search(diff) or _TEST_DIR_RE.search(diff):
        label = "TEST"
        confidence = 0.88

    if ast_signals.import_churn >= 3 and label == "ARCHITECTURE":
        confidence = min(1.0, confidence + 0.1)

    return CommitRecord(
        sha=sha,
        label=label,
        confidence=confidence,
        ast_signals=ast_signals,
        repo=repo,
        date=date,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        message=message,
    )
