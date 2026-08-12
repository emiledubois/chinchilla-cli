"""Pruebas del cargador de bancos de preguntas declarativos (YAML)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models.assessment import QuestionModule
from src.questions import CYBERSECURITY_QUESTIONS, DATA_PROTECTION_QUESTIONS, OWASP_QUESTIONS
from src.questions.loader import QuestionBankError, load_question_bank


@pytest.mark.parametrize(
    "bank",
    [CYBERSECURITY_QUESTIONS, DATA_PROTECTION_QUESTIONS, OWASP_QUESTIONS],
)
def test_real_banks_have_at_least_ten_unique_questions(bank) -> None:
    assert len(bank) >= 10
    assert len({q.id for q in bank}) == len(bank)


def test_load_question_bank_rejects_missing_file(tmp_path: Path) -> None:
    # DATA_DIR está fijo dentro del paquete; se prueba contra un archivo
    # inexistente pasando un nombre que no existe en src/questions/data/.
    with pytest.raises(QuestionBankError, match="no encontrado"):
        load_question_bank("no-existe.yaml", QuestionModule.OWASP)


def test_load_question_bank_rejects_fewer_than_ten_questions(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "short.yaml").write_text(
        "- id: q1\n  category: c\n  weight: 1\n  text: '?'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("src.questions.loader.DATA_DIR", data_dir)

    with pytest.raises(QuestionBankError, match="al menos 10"):
        load_question_bank("short.yaml", QuestionModule.OWASP)


def test_load_question_bank_rejects_duplicate_ids(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    entries = "\n".join(f"- id: dup\n  category: c\n  weight: 1\n  text: 'q{i}'" for i in range(11))
    (data_dir / "dupes.yaml").write_text(entries, encoding="utf-8")
    monkeypatch.setattr("src.questions.loader.DATA_DIR", data_dir)

    with pytest.raises(QuestionBankError, match="duplicado"):
        load_question_bank("dupes.yaml", QuestionModule.OWASP)


def test_load_question_bank_rejects_invalid_weight(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    entries = "\n".join(f"- id: q{i}\n  category: c\n  weight: 1\n  text: 'q{i}'" for i in range(10))
    entries = entries.replace("weight: 1\n  text: 'q0'", "weight: 99\n  text: 'q0'")
    (data_dir / "badweight.yaml").write_text(entries, encoding="utf-8")
    monkeypatch.setattr("src.questions.loader.DATA_DIR", data_dir)

    with pytest.raises(QuestionBankError, match="inválida"):
        load_question_bank("badweight.yaml", QuestionModule.OWASP)


def test_load_question_bank_rejects_non_list_top_level(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "notalist.yaml").write_text("not_a_list: true\n", encoding="utf-8")
    monkeypatch.setattr("src.questions.loader.DATA_DIR", data_dir)

    with pytest.raises(QuestionBankError, match="lista de preguntas"):
        load_question_bank("notalist.yaml", QuestionModule.OWASP)
