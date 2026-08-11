"""Remediación agéntica supervisada.

Principio de diseño (ver specs/THREAT_MODEL.md, sección "Elevation of
Privilege"): este módulo NUNCA genera código libremente. Solo invoca
herramientas deterministas ya auditadas (`ruff --fix`, bump de versión
de dependencia a partir de un `fix_version` reportado por `pip-audit`),
y nunca escribe a disco sin una aprobación humana explícita por cada
cambio propuesto (ASI09 — sin autoaprobación).
"""
