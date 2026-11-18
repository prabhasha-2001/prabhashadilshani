FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=wsgi.py

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/
COPY docker/entrypoint.sh /usr/local/bin/prabhashadilshani-entrypoint
RUN chmod +x /usr/local/bin/prabhashadilshani-entrypoint \
    && mkdir -p /data/uploads /data/backups /data/knowledge /data/index \
    && groupadd --system prabhashadilshani \
    && useradd --system --gid prabhashadilshani --home-dir /app prabhashadilshani \
    && chown -R prabhashadilshani:prabhashadilshani /app /data

ENV UPLOAD_DIR=/data/uploads \
    BACKUP_DIR=/data/backups \
    KNOWLEDGE_DIR=/data/knowledge \
    FAISS_INDEX_DIR=/data/index \
    GUNICORN_WORKERS=3

USER prabhashadilshani

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:5000/api/v1/health || exit 1

ENTRYPOINT ["prabhashadilshani-entrypoint"]
