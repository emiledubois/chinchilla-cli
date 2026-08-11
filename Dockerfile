# Sandbox de ejecución (ASI05 - Unexpected Code Execution): todo código de
# agentes y toda corrida de la CLI ocurre dentro de este contenedor, nunca
# directamente en el host.
FROM python:3.11-slim

# Usuario sin privilegios (ASI03 - Identity Abuse / defensa en profundidad).
RUN useradd --create-home --uid 1000 preaudit
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/logs /app/reports && chown -R preaudit:preaudit /app

USER preaudit

ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--help"]
