"""Prueba e2e: simula una corrida completa de `preaudit run` vía CliRunner."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from src.cli import preaudit
from src.models.assessment import QuestionModule
from src.questions import QUESTIONS_BY_MODULE


def test_full_run_generates_pdf_report(tmp_path: Path) -> None:
    n_questions = len(QUESTIONS_BY_MODULE[QuestionModule.CYBERSECURITY])

    inputs = [
        "1",  # módulo: Ciberseguridad
        "",  # nombre de empresa: usar default
    ]
    for _ in range(n_questions):
        inputs.append("1")  # respuesta: "Sí"
        inputs.append("")  # comentario: omitir
    inputs.append("y")  # confirmar generación de PDF

    runner = CliRunner()
    result = runner.invoke(
        preaudit,
        ["run", "--output-dir", str(tmp_path)],
        input="\n".join(inputs) + "\n",
    )

    assert result.exit_code == 0, result.output
    assert "Informe generado" in result.output

    generated_files = list(tmp_path.glob("*.pdf"))
    assert len(generated_files) == 1

    report_path = generated_files[0]
    assert report_path.stat().st_size > 0
    assert (report_path.stat().st_mode & 0o777) == 0o600
