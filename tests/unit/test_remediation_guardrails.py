"""Pruebas de los guardrails de alcance del módulo de remediación (ASI02)."""

from __future__ import annotations

import pytest

from src.remediation.guardrails import is_target_allowed


@pytest.mark.parametrize(
    "target_file",
    [
        "src/cli.py",
        "src/certification/models.py",
        "tests/unit/test_models.py",
        "requirements.txt",
    ],
)
def test_allowed_targets(target_file: str) -> None:
    assert is_target_allowed(target_file) is True


@pytest.mark.parametrize(
    "target_file",
    [
        "",
        "/etc/passwd",
        "~/.bashrc",
        "../outside.py",
        "src/../../../etc/passwd",
        ".claude/agents/architect.md",
        "Dockerfile",
        "scripts/audit-log.sh",
        "specs/SPEC.md",
        "logs/audit.log",
    ],
)
def test_disallowed_targets(target_file: str) -> None:
    assert is_target_allowed(target_file) is False
