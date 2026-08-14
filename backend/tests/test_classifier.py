from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.classifier import _analyze_diff, classify_commit

NOW = datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("message", "expected_label", "expected_confidence"),
    [
        ("feat: add dashboard", "FEATURE", 0.9),
        ("added auth flow", "FEATURE", 0.9),
        ("implement pagination", "FEATURE", 0.9),
        ("introduce cache", "FEATURE", 0.9),
        ("new feature: ranking", "FEATURE", 0.9),
        ("fix: handle null", "BUGFIX", 0.9),
        ("hotfix memory leak", "BUGFIX", 0.9),
        ("resolve regression in worker", "BUGFIX", 0.9),
        ("patch crash in parser", "BUGFIX", 0.9),
        ("refactor: simplify handlers", "REFACTOR", 0.9),
        ("clean module structure", "REFACTOR", 0.9),
        ("reorganize imports", "REFACTOR", 0.9),
        ("test: add classifier tests", "TEST", 0.9),
        ("unittest for github client", "TEST", 0.9),
        ("increase coverage for auth", "TEST", 0.7),
        ("docs: update readme", "DOCS", 0.9),
        ("add docstring for helper", "DOCS", 0.7),
        ("changelog update", "DOCS", 0.9),
        ("docs: add changelog", "DOCS", 0.9),
        ("chore: bump deps", "CHORE", 0.9),
        ("upgrade ci workflow", "CHORE", 0.9),
        ("build: adjust lint job", "CHORE", 0.9),
        ("major redesign of parsing", "ARCHITECTURE", 0.7),
        ("initial commit", "ARCHITECTURE", 0.9),
        ("misc maintenance", "CHORE", 0.3),
    ],
)
def test_message_patterns_cover_all_labels(message: str, expected_label: str, expected_confidence: float) -> None:
    record = classify_commit(
        sha="abc123",
        message=message,
        diff="",
        repo="octocat/repo",
        date=NOW,
        lines_added=10,
        lines_deleted=2,
    )

    assert record.label == expected_label
    assert record.confidence == pytest.approx(expected_confidence)


def test_feature_pattern_non_start_match_gets_0_7_confidence() -> None:
    record = classify_commit(
        sha="abc123",
        message="ui tweak then create endpoint",
        diff="",
        repo="octocat/repo",
        date=NOW,
        lines_added=8,
        lines_deleted=1,
    )

    assert record.label == "FEATURE"
    assert record.confidence == pytest.approx(0.7)


def test_ast_override_to_architecture() -> None:
    diff = """
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@
+def f1(x):
+    if x:
+        return 1
+    return 0
+
+def f2(x):
+    if x:
+        return 1
+    return 0
+
+def f3(x):
+    if x:
+        return 1
+    return 0
+
+def f4(x):
+    if x:
+        return 1
+    return 0
+
+def f5(x):
+    if x:
+        return 1
+    return 0
+"""
    record = classify_commit(
        sha="abc123",
        message="chore: tidy",
        diff=diff,
        repo="octocat/repo",
        date=NOW,
        lines_added=120,
        lines_deleted=3,
    )

    assert record.label == "ARCHITECTURE"
    assert record.confidence == pytest.approx(0.85)
    assert record.ast_signals.fn_delta >= 5
    assert record.ast_signals.complexity_delta >= 10


def test_ast_override_to_test_from_filename_marker() -> None:
    diff = """
diff --git a/app/core.py b/tests/test_core.py
--- a/app/core.py
+++ b/tests/test_core.py
@@
+def test_behaviour():
+    assert True
+"""
    record = classify_commit(
        sha="abc123",
        message="chore: update files",
        diff=diff,
        repo="octocat/repo",
        date=NOW,
        lines_added=5,
        lines_deleted=0,
    )

    assert record.label == "TEST"
    assert record.confidence == pytest.approx(0.88)


def test_refactor_boost_when_negative_fn_and_more_deletions() -> None:
    diff = """
diff --git a/mod.py b/mod.py
--- a/mod.py
+++ b/mod.py
@@
-def old_one():
-    return 1
-
-def old_two():
-    return 2
+def old_one():
+    return 1
+"""
    record = classify_commit(
        sha="abc123",
        message="fix: remove dead code",
        diff=diff,
        repo="octocat/repo",
        date=NOW,
        lines_added=1,
        lines_deleted=10,
    )

    assert record.label == "REFACTOR"
    assert record.confidence == pytest.approx(0.9)


def test_import_churn_boosts_architecture_confidence() -> None:
    diff = """
diff --git a/service.py b/service.py
--- a/service.py
+++ b/service.py
@@
+import os
+import re
+import math
+import json
+
+def f1(x):
+    if x:
+        return 1
+    return 0
+
+def f2(x):
+    if x:
+        return 1
+    return 0
+
+def f3(x):
+    if x:
+        return 1
+    return 0
+
+def f4(x):
+    if x:
+        return 1
+    return 0
+
+def f5(x):
+    if x:
+        return 1
+    return 0
+"""
    record = classify_commit(
        sha="abc123",
        message="chore: prepare",
        diff=diff,
        repo="octocat/repo",
        date=NOW,
        lines_added=150,
        lines_deleted=0,
    )

    assert record.label == "ARCHITECTURE"
    assert record.ast_signals.import_churn >= 3
    assert record.confidence == pytest.approx(0.95)


def test_empty_diff_returns_zero_signals() -> None:
    signals = _analyze_diff("")

    assert signals.fn_delta == 0
    assert signals.class_delta == 0
    assert signals.complexity_delta == 0.0
    assert signals.import_churn == 0
    assert signals.file_count_delta == 0


def test_malformed_python_diff_is_handled_gracefully() -> None:
    diff = """
diff --git a/bad.py b/bad.py
--- a/bad.py
+++ b/bad.py
@@
+def broken(:
+    return 1
+"""
    signals = _analyze_diff(diff)

    assert signals.fn_delta == 0
    assert signals.class_delta == 0
    assert signals.import_churn == 0


def test_confidence_always_within_range() -> None:
    cases = [
        ("misc", ""),
        ("feat: x", ""),
        (
            "chore",
            """
diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@
+def f1(x):
+    if x:
+        return 1
+    return 0
+def f2(x):
+    if x:
+        return 1
+    return 0
+def f3(x):
+    if x:
+        return 1
+    return 0
+def f4(x):
+    if x:
+        return 1
+    return 0
+def f5(x):
+    if x:
+        return 1
+    return 0
+""",
        ),
    ]

    for message, diff in cases:
        record = classify_commit(
            sha="abc123",
            message=message,
            diff=diff,
            repo="octocat/repo",
            date=NOW,
            lines_added=25,
            lines_deleted=3,
        )
        assert 0.0 <= record.confidence <= 1.0
