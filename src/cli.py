"""Punto de entrada de `preaudit-cli` (Click + Rich).

Flujo: saludo -> selección de módulo -> cuestionario pregunta a pregunta
-> resumen de puntajes -> generación de PDF (opcional, tras confirmación
explícita del usuario — ver ASI09 en .claude/skills/security-scan.md).
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from src.certification.evidence import collect_all_evidence
from src.certification.report import generate_certification_report
from src.certification.runner import run_certification
from src.models.assessment import (
    DEFAULT_COMPANY_NAME,
    Answer,
    AnswerOption,
    Assessment,
    Question,
    QuestionModule,
)
from src.questions import QUESTIONS_BY_MODULE
from src.remediation.applier import RemediationScopeError, apply_fix
from src.remediation.proposer import propose_fixes
from src.report.generator import generate_report
from src.utils.security import sanitize_input

console = Console()

CERTIFICATION_DECISION_COLOR: dict[str, str] = {
    "Otorgar": "green",
    "Otorgar con condiciones": "yellow",
    "Denegar": "red",
}

MODULE_LABELS: dict[str, str] = {
    "cybersecurity": "Ciberseguridad (Ley 21.663)",
    "data_protection": "Protección de Datos (Ley 21.719)",
    "owasp": "OWASP Top 10",
}

RISK_COLOR: dict[str, str] = {
    "Bajo": "green",
    "Medio": "yellow",
    "Alto": "dark_orange",
    "Crítico": "red",
}

# Opciones de menú de módulo -> lista de QuestionModule a incluir.
_MODULE_MENU: dict[str, tuple[str, list[QuestionModule]]] = {
    "1": ("Ciberseguridad (Ley 21.663)", [QuestionModule.CYBERSECURITY]),
    "2": ("Protección de Datos (Ley 21.719)", [QuestionModule.DATA_PROTECTION]),
    "3": ("OWASP Top 10", [QuestionModule.OWASP]),
    "4": (
        "Todos los módulos",
        [QuestionModule.CYBERSECURITY, QuestionModule.DATA_PROTECTION, QuestionModule.OWASP],
    ),
}


def _print_welcome() -> None:
    console.print(
        Panel.fit(
            "[bold]preaudit-cli[/bold]\n"
            "Preauditoría de cumplimiento — Ley 21.663 (Ciberseguridad), "
            "Ley 21.719 (Protección de Datos Personales, vigencia "
            "1-dic-2026) y OWASP Top 10.\n\n"
            "[dim]Este cuestionario es un autodiagnóstico preliminar y NO "
            "reemplaza una auditoría formal.[/dim]",
            title="Bienvenido",
            border_style="blue",
        )
    )


def _select_modules() -> list[QuestionModule]:
    table = Table(title="Módulos disponibles", header_style="bold blue")
    table.add_column("Opción", justify="center")
    table.add_column("Módulo")
    for key, (label, _modules) in _MODULE_MENU.items():
        table.add_row(key, label)
    console.print(table)

    choice = Prompt.ask(
        "Selecciona un módulo",
        choices=list(_MODULE_MENU.keys()),
        default="4",
        show_choices=False,
    )
    return _MODULE_MENU[choice][1]


def _ask_question(question: Question, index: int, total: int) -> Answer:
    console.rule(f"Pregunta {index}/{total} — [cyan]{question.category}[/cyan]")
    console.print(question.text)
    for option in AnswerOption:
        console.print(f"  [{option.value + 1}] {option.label}")

    raw_choice = Prompt.ask(
        "Respuesta",
        choices=[str(option.value + 1) for option in AnswerOption],
        show_choices=False,
    )
    selected = AnswerOption(int(raw_choice) - 1)

    raw_comment = Prompt.ask("Comentario (opcional, Enter para omitir)", default="")
    comment = sanitize_input(raw_comment, max_length=500) if raw_comment else None
    return Answer(question_id=question.id, selected_option=selected, comment=comment or None)


def _render_summary(assessment: Assessment) -> None:
    table = Table(title="Resultado de la preauditoría", header_style="bold blue")
    table.add_column("Módulo")
    table.add_column("Puntaje", justify="right")
    for module_key, score in assessment.scores.items():
        if module_key == "total":
            continue
        table.add_row(MODULE_LABELS.get(module_key, module_key), f"{score:.1f}%")
    console.print(table)

    risk_label = assessment.risk_level.value if assessment.risk_level else "N/A"
    color = RISK_COLOR.get(risk_label, "white")
    console.print(f"\n[bold]Puntaje total:[/bold] {assessment.scores.get('total', 0.0):.1f}%")
    console.print(f"[bold]Nivel de riesgo:[/bold] [{color}]{risk_label}[/{color}]")


@click.group()
@click.version_option(package_name="preaudit-cli")
def preaudit() -> None:
    """preaudit-cli — herramienta de preauditoría de cumplimiento normativo chileno."""


@preaudit.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("reports"),
    show_default=True,
    help="Directorio donde se guarda el PDF generado.",
)
@click.option(
    "--company-name",
    default=None,
    help="Nombre de la empresa (opcional). Es el único dato identificable que se solicita.",
)
def run(output_dir: Path, company_name: str | None) -> None:
    """Ejecuta el cuestionario interactivo y genera el informe PDF."""
    _print_welcome()

    modules = _select_modules()
    if company_name is None:
        company_name = Prompt.ask("Nombre de la empresa (opcional)", default=DEFAULT_COMPANY_NAME)

    selected_questions: list[Question] = []
    for module in modules:
        selected_questions.extend(QUESTIONS_BY_MODULE[module])

    console.print(f"\n[dim]Se realizarán {len(selected_questions)} preguntas.[/dim]")

    total = len(selected_questions)
    answers: list[Answer] = [
        _ask_question(question, index, total) for index, question in enumerate(selected_questions, start=1)
    ]

    assessment = Assessment(company_name=company_name, answers=answers)
    assessment.compute_scores(selected_questions)

    console.print()
    _render_summary(assessment)

    if not Confirm.ask("\n¿Generar informe PDF con estos resultados?", default=True):
        console.print("[yellow]Operación cancelada: no se generó ningún archivo.[/yellow]")
        return

    output_path = generate_report(assessment, selected_questions, output_dir)
    console.print(f"\n[bold green]Informe generado:[/bold green] {output_path}")
    console.print("[dim]Permisos del archivo restringidos a 0600. " "Evento registrado en logs/audit.log.[/dim]")


@preaudit.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("reports/certification"),
    show_default=True,
    help="Directorio donde se guarda el informe de certificación.",
)
@click.option(
    "--organization",
    default="preaudit-cli (auto-certificación)",
    help="Nombre del proyecto/organización auditada.",
)
@click.option(
    "--project-root",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=Path("."),
    show_default=True,
    help="Raíz del proyecto a auditar (debe contener src/ y tests/).",
)
def certify(output_dir: Path, organization: str, project_root: Path) -> None:
    """Ejecuta pytest/ruff/bandit como evidencia y genera el informe de certificación."""
    console.print(
        Panel.fit(
            "[bold]preaudit certify[/bold]\n"
            "Aseguramiento de calidad y seguridad — plan de pruebas, casos de "
            "prueba formales, obtención de evidencias e informe de "
            "certificación (IEEE 829 / ISO 17021-1 / ISO 17065 / ISO 19011).\n\n"
            "[dim]Ejecutando pytest, ruff y bandit sobre el proyecto...[/dim]",
            title="Certificación de calidad y seguridad",
            border_style="blue",
        )
    )

    report = run_certification(project_root, organization=organization)

    table = Table(title="Resumen de hallazgos", header_style="bold blue")
    table.add_column("Categoría")
    table.add_column("Cantidad", justify="right")
    table.add_row("Conformidades", str(len(report.conformities)))
    table.add_row("No conformidades mayores", str(len(report.major_nonconformities)))
    table.add_row("No conformidades menores", str(len(report.minor_nonconformities)))
    table.add_row("Observaciones", str(len(report.observations)))
    console.print(table)

    color = CERTIFICATION_DECISION_COLOR.get(report.decision.value, "white")
    console.print(f"\n[bold]Decisión:[/bold] [{color}]{report.decision.value}[/{color}]")
    console.print(report.decision_justification)

    output_path = generate_certification_report(report, output_dir)
    console.print(f"\n[bold green]Informe de certificación generado:[/bold green] {output_path}")
    console.print("[dim]Permisos del archivo restringidos a 0600. Evento registrado en logs/audit.log.[/dim]")

    if report.decision.value == "Denegar":
        raise SystemExit(1)


@preaudit.command()
@click.option(
    "--project-root",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=Path("."),
    show_default=True,
    help="Raíz del proyecto sobre el que proponer remediaciones.",
)
def remediate(project_root: Path) -> None:
    """Propone fixes deterministas (ruff/dependencias) y los aplica solo con aprobación explícita."""
    console.print(
        Panel.fit(
            "[bold]preaudit remediate[/bold]\n"
            "Remediación agéntica supervisada: SOLO invoca herramientas "
            "deterministas ya auditadas (ruff --fix, bump de dependencias "
            "con fix conocido). Cada cambio se muestra como diff y requiere "
            "tu aprobación explícita antes de tocar disco — nunca se "
            "autoaprueba (ver ASI09 en .claude/skills/security-scan.md).",
            title="Remediación",
            border_style="blue",
        )
    )

    console.print("[dim]Recolectando evidencia (pytest, ruff, bandit, pip-audit)...[/dim]")
    findings, _failed = collect_all_evidence(project_root)
    proposals = propose_fixes(findings, project_root)

    if not proposals:
        console.print("\n[green]No hay fixes automáticos disponibles en este momento.[/green]")
        return

    applied = 0
    for proposal in proposals:
        console.print()
        console.print(
            Panel(
                Syntax(proposal.diff, "diff", theme="ansi_dark", word_wrap=True),
                title=f"{proposal.tool.value} — {proposal.target_file}",
                border_style="yellow",
            )
        )
        console.print(proposal.description)
        if Confirm.ask("¿Aplicar este cambio?", default=False):
            try:
                apply_fix(proposal, project_root)
                applied += 1
                console.print("[green]Aplicado y registrado en logs/audit.log.[/green]")
            except RemediationScopeError as exc:
                console.print(f"[red]Rechazado por guardrail de alcance: {exc}[/red]")
        else:
            console.print("[dim]Omitido por el usuario.[/dim]")

    console.print(f"\n[bold]{applied}/{len(proposals)}[/bold] cambio(s) aplicado(s).")


if __name__ == "__main__":
    preaudit()
