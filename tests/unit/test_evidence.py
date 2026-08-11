"""Pruebas de la capa de recolección de evidencia (src/certification/evidence.py)."""

from __future__ import annotations

from pathlib import Path

from src.certification.evidence import collect_ruff_findings
from src.remediation.guardrails import is_target_allowed
from src.remediation.proposer import propose_ruff_fix


def test_collect_ruff_findings_returns_paths_relative_to_project_root(tmp_path: Path) -> None:
    """Regresión: `ruff --output-format json` siempre reporta rutas ABSOLUTAS,
    sin importar cómo se le haya invocado. Si `Finding.location` no se
    normaliza a relativa a `project_root`, `is_target_allowed()` la rechaza
    (empieza con '/') y `preaudit remediate` nunca propone nada, en
    silencio, incluso habiendo hallazgos auto-corregibles reales. Este bug
    ocurrió de verdad y no lo detectaron los tests con `Finding` fabricados
    a mano (ver tests/unit/test_remediation.py) — solo una corrida real de
    principio a fin lo reveló."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "bad.py").write_text("import os\nx = 1\n", encoding="utf-8")

    findings = collect_ruff_findings(tmp_path, ["src"])

    real_findings = [f for f in findings if f.id != "ruff-clean"]
    assert real_findings, "se esperaba al menos un hallazgo de ruff (import no usado)"
    for finding in real_findings:
        assert not finding.location.startswith("/"), finding.location
        target_file = finding.location.split(":")[0]
        assert is_target_allowed(target_file), target_file


def test_propose_ruff_fix_works_end_to_end_with_real_evidence(tmp_path: Path) -> None:
    """Prueba de integración completa: evidencia real (no un Finding fabricado)
    -> propuesta -> diff no vacío. Reproduce exactamente el escenario que
    reveló el bug de rutas absolutas."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "bad.py").write_text("import os\nx = 1\n", encoding="utf-8")

    findings = collect_ruff_findings(tmp_path, ["src"])
    proposals = [propose_ruff_fix(f, tmp_path) for f in findings if f.id != "ruff-clean"]
    proposals = [p for p in proposals if p is not None]

    assert proposals, "se esperaba al menos una propuesta de fix"
