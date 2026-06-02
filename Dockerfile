FROM nikolaik/python-nodejs:python3.12-nodejs20-slim AS frontend-builder

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
    biber \
    build-essential \
    fontconfig \
    fonts-noto-cjk \
    ghostscript \
    latexmk \
    texlive-bibtex-extra \
    texlive-fonts-recommended \
    texlive-lang-chinese \
    texlive-lang-japanese \
    texlive-latex-extra \
    texlive-luatex \
    texlive-pictures \
    texlive-plain-generic \
    texlive-publishers \
    texlive-science \
    texlive-xetex \
    curl \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install BabelDOC==0.5.23

COPY backend ./backend
COPY terms ./terms
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY start.sh ./start.sh

RUN mkdir -p runtime/tasks runtime/uploads
RUN chmod +x /app/start.sh

EXPOSE 8000
CMD ["./start.sh"]