FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python - <<'PY'
from pathlib import Path
raw = Path("requirements.txt").read_bytes()
for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be"):
    try:
        text = raw.decode(encoding)
        break
    except UnicodeDecodeError:
        continue
else:
    raise UnicodeDecodeError("requirements.txt", raw, 0, 1, "unsupported encoding")
Path("requirements.docker.txt").write_text(text, encoding="utf-8")
PY
RUN pip install --upgrade pip && pip install -r requirements.docker.txt
RUN pip install BabelDOC==0.5.23

COPY backend ./backend
COPY terms ./terms
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p runtime/tasks runtime/uploads

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
