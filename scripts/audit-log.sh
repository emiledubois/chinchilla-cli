#!/usr/bin/env bash
# audit-log.sh — Trazabilidad de compliance para el workspace agéntico.
#
# Registra QUIÉN (actor), QUÉ (action), CUÁNDO (timestamp UTC) y CON QUÉ
# FINALIDAD (purpose) se generó o tocó un artefacto, junto al hash SHA-256
# del artefacto si corresponde. Requisito de trazabilidad de Ley 21.633
# (gestión de incidentes/activos) y Ley 21.719 (registro de operaciones de
# tratamiento) — ver specs/SPEC.md §7 y .claude/skills/compliance-check.md.
#
# Uso: audit-log.sh <actor> <action> <purpose> [artifact_hash]
#
# Se invoca SIEMPRE con argumentos ya sanitizados por
# src/utils/security.py::record_audit_event, pasados como lista (nunca
# `shell=True`), lo que evita inyección de comandos (A03 / ASI02).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"
LOG_DIR="$REPO_ROOT/logs"
LOG_FILE="$LOG_DIR/audit.log"

if [[ $# -lt 3 ]]; then
  echo "Uso: $0 <actor> <action> <purpose> [artifact_hash]" >&2
  exit 1
fi

ACTOR="$1"
ACTION="$2"
PURPOSE="$3"
ARTIFACT_HASH="${4:--}"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Formato: timestamp | actor | action | purpose | artifact_sha256
printf '%s | actor=%s | action=%s | purpose=%s | sha256=%s\n' \
  "$TIMESTAMP" "$ACTOR" "$ACTION" "$PURPOSE" "$ARTIFACT_HASH" >> "$LOG_FILE"
