# Dockerfile (V12 - Universal con Python y Node.js)
FROM python:3.11-slim

# --- Sección de Herramientas Base ---
RUN apt-get update && apt-get install -y git curl

# --- Sección de Python ---
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Sección de Node.js y Cypress (para el Agente E2E) ---
RUN apt-get install -y nodejs npm
RUN npm install -g cypress

# --- Configuración Final ---
COPY src/ .
CMD ["python", "-u", "agent_runner.py"]