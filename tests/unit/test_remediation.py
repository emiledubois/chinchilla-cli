"""Pruebas del ciclo propuesta -> aprobación -> aplicación de remediación."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.certification.models import Finding, FindingType
from src.remediation.applier import RemediationScopeError, apply_fix
from src.remediation.models import ProposedFix, RemediationOutcome, RemediationTool
from src.remediation.proposer import propose_dependency_bump, propose_ruff_fix


def _finding(**overrides) -> Finding:
    defaults = {
        "id": "f1",
        "type": FindingType.NO_CONFORMIDAD_MENOR,
        "description": "unused import",
        "objective_evidence": "e",
        "location": "src/bad.py:1",
        "source_tool": "ruff",
    }
    defaults.update(overrides)
    return Finding(**defaults)


def test_propose_ruff_fix_ignores_major_findings() -> None:
    finding = _finding(type=FindingType.NO_CONFORMIDAD_MAYOR)
    assert propose_ruff_fix(finding, Path(".")) is None


def test_propose_ruff_fix_ignores_non_ruff_findings() -> None:
    finding = _finding(source_tool="bandit")
    assert propose_ruff_fix(finding, Path(".")) is None


def test_propose_ruff_fix_generates_a_preview_diff_without_touching_the_file(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    target = src_dir / "bad.py"
    target.write_text("import os\nx = 1\n", encoding="utf-8")

    proposal = propose_ruff_fix(_finding(), tmp_path)

    assert proposal is not None
    assert proposal.tool == RemediationTool.RUFF_FIX
    assert "os" in proposal.diff
    assert "import os" in target.read_text(encoding="utf-8")  # --diff no aplica nada


def test_apply_fix_rejects_targets_outside_the_allow_list() -> None:
    forged_fix = ProposedFix(
        finding_id="f1",
        tool=RemediationTool.RUFF_FIX,
        target_file="../outside.py",
        description="d",
        diff="--- a\n+++ b\n",
    )
    with pytest.raises(RemediationScopeError):
        apply_fix(forged_fix, Path("."))


def test_apply_fix_ruff_actually_fixes_the_file(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    target = src_dir / "bad.py"
    target.write_text("import os\nx = 1\n", encoding="utf-8")

    proposal = propose_ruff_fix(_finding(), tmp_path)
    assert proposal is not None

    result = apply_fix(proposal, tmp_path)

    assert result.outcome == RemediationOutcome.APPLIED
    assert "import os" not in target.read_text(encoding="utf-8")


def test_propose_dependency_bump_short_circuits_without_requirements_file(tmp_path: Path) -> None:
    finding = _finding(source_tool="pip-audit", location="requirements.txt:click")
    assert propose_dependency_bump(finding, tmp_path) is None


def test_apply_fix_dependency_bump_rejects_a_stale_diff(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("click==8.3.3\n", encoding="utf-8")
    stale_fix = ProposedFix(
        finding_id="f1",
        tool=RemediationTool.DEPENDENCY_BUMP,
        target_file="requirements.txt",
        description="d",
        diff="--- requirements.txt\n+++ requirements.txt\n@@ line 1 @@\n-click==8.1.7\n+click==8.3.3\n",
    )
    with pytest.raises(RemediationScopeError):
        apply_fix(stale_fix, tmp_path)
