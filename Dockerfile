FROM nikolaik/python-nodejs:python3.12-nodejs22-slim AS frontend-builder

ARG TARGETARCH

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
RUN printf '%s' "$TARGETARCH" > /tmp/targetarch
RUN python3 - <<'PY'
import json
import subprocess
from pathlib import Path

target_arch = Path("/tmp/targetarch").read_text(encoding="utf-8").strip()
suffix_by_arch = {
    "arm64": "linux-arm64-gnu",
    "amd64": "linux-x64-gnu",
}
suffix = suffix_by_arch.get(target_arch)
if not suffix:
    print(f"Skipping native optional dependency install for TARGETARCH={target_arch}")
    raise SystemExit(0)

package_lock = json.loads(Path("package-lock.json").read_text(encoding="utf-8"))
packages = package_lock.get("packages", {})
install_specs: list[str] = []
for package_name, package_meta in packages.items():
    if not package_name.startswith("node_modules/"):
        continue
    dependencies = package_meta.get("optionalDependencies", {})
    for dependency_name, dependency_version in dependencies.items():
        if dependency_name.endswith(suffix):
            install_specs.append(f"{dependency_name}@{dependency_version}")

if not install_specs:
    print(f"No matching native optional dependencies found for {suffix}")
    raise SystemExit(0)

subprocess.run(["npm", "install", "--no-save", *sorted(set(install_specs))], check=True)
PY

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
