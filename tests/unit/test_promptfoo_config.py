"""Validación estructural de `promptfooconfig.yaml` (sin llamar a ningún LLM).

`promptfoo eval` real requiere ANTHROPIC_API_KEY y solo corre en CI
(security-scan.yml, job agentic-prompt-scan). Esta prueba valida lo que
sí se puede verificar sin red ni credenciales: que la config es YAML
válido, que cada `system_prompt: file://...` apunta a un agente real
existente, y que los 4 agentes están cubiertos — para detectar drift
(p.ej. si se agrega/renombra un agente y se olvida actualizar la config)
en el pipeline normal de pytest, no solo en el job de promptfoo.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "promptfooconfig.yaml"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"


def _load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_promptfoo_config_is_valid_yaml_with_expected_top_level_keys() -> None:
    config = _load_config()
    assert set(config) >= {"prompts", "providers", "tests"}
    assert isinstance(config["tests"], list) and len(config["tests"]) > 0


def test_promptfoo_template_file_referenced_by_prompts_exists() -> None:
    config = _load_config()
    for prompt_ref in config["prompts"]:
        assert (REPO_ROOT / prompt_ref).is_file(), f"prompt no encontrado: {prompt_ref}"


def test_every_test_case_references_an_existing_agent_file() -> None:
    config = _load_config()
    for test_case in config["tests"]:
        system_prompt_ref = test_case["vars"]["system_prompt"]
        assert system_prompt_ref.startswith("file://"), test_case["description"]
        agent_path = REPO_ROOT / system_prompt_ref.removeprefix("file://")
        assert agent_path.is_file(), f"{test_case['description']}: {agent_path} no existe"


def test_all_four_agents_are_covered_by_at_least_one_test_case() -> None:
    config = _load_config()
    referenced_agents = {Path(tc["vars"]["system_prompt"].removeprefix("file://")).stem for tc in config["tests"]}
    agent_files = {path.stem for path in AGENTS_DIR.glob("*.md")}
    assert referenced_agents == agent_files


def test_prompt_template_has_no_bare_delimiter_line() -> None:
    """Regresión: una línea con solo '---' en el template hace que promptfoo
    la interprete como separador de múltiples prompts en un mismo archivo,
    partiendo cada test en 2 evaluaciones (una de ellas sin system_prompt).
    Ver specs/TEST_PLAN.md."""
    config = _load_config()
    for prompt_ref in config["prompts"]:
        content = (REPO_ROOT / prompt_ref).read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines()]
        assert "---" not in lines, f"{prompt_ref} tiene una línea '---' que promptfoo interpreta como delimitador"
