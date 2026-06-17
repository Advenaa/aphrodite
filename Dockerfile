# syntax=docker/dockerfile:1

# ---- Build stage: install the package into an isolated venv ----
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src

# pyproject reads the version from aphrodite.__version__ and the readme from
# README.md, so both must be present for the build. Copy them with the package.
COPY pyproject.toml README.md ./
COPY aphrodite ./aphrodite

# Install into a self-contained venv so the runtime image carries no build
# toolchain. Add the [acp] extra; drop it if you do not need the ACP relay.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install ".[acp]"

# ---- Runtime stage: minimal, non-root ----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APHRODITE_HOST=0.0.0.0 \
    APHRODITE_PORT=9079

# Carry only the prebuilt venv; no compiler or build files in the final image.
COPY --from=builder /opt/venv /opt/venv

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 aphrodite
USER aphrodite
WORKDIR /home/aphrodite

EXPOSE 9079

# The app defaults to 127.0.0.1 for bare-metal safety; a container must bind
# 0.0.0.0 to be reachable. The uvicorn --host flag is the authoritative bind.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9079/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "aphrodite.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "9079"]
