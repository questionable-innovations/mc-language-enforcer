# Speech judge for the Language Enforcer Minecraft mod.
# GPU: docker run --gpus all ... (needs the NVIDIA Container Toolkit). Works on GTX 10xx (Pascal) and newer.
# CPU: drop --gpus. LE_MODEL=auto picks small on a GPU, base on CPU (both are baked in).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --extra gpu --no-install-project
COPY langenforcer_sidecar ./langenforcer_sidecar
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --extra gpu

ENV PATH=/app/.venv/bin:$PATH \
    LE_MODEL=auto \
    LE_MODEL_DIR=/models \
    HF_HUB_DISABLE_TELEMETRY=1
# Bake the default models in so the container starts offline
RUN python -m langenforcer_sidecar download small && python -m langenforcer_sidecar download base

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/healthz')"
CMD ["python", "-m", "langenforcer_sidecar"]
