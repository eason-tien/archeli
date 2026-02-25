# ArcHeli v1.0.0 — Dockerfile
# Build:  docker build -t archeli .
# Run:    docker run -p 8000:8000 --env-file .env archeli

FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data directories
RUN mkdir -p /app/evidence /app/data

# Environment defaults (override via --env-file or -e flags)
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DB_PATH=/app/data/archeli.db \
    SKILLS_DIR=/app/app/skills \
    EVIDENCE_DIR=/app/evidence \
    ROUTING_RULES_PATH=/app/configs/routing_rules.yaml \
    LOG_LEVEL=INFO

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
