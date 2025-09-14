# ------------------------------------------------------------------------------
# mock_api — Dockerfile used by docker-compose `build: ./mock_api`
#
# Build context:
# - In docker-compose.yml:
#     mock-api:
#       build: ./mock_api
#   → Compose sends the ./mock_api folder as the *build context* to the Docker daemon.
#   → Docker looks for `./mock_api/Dockerfile` (unless `dockerfile:` overrides it).
#   → Instructions below define how to *build an image* for the mock_api service.
# ------------------------------------------------------------------------------

FROM python:3.11-slim
# Base image — Debian slim + CPython 3.11 preinstalled.
# - Debian slim: a minimal Debian Linux image with extra packages, docs, and
#   localization removed to reduce size and attack surface.
# - CPython: the standard/reference Python implementation (written in C). This is
#   the regular Python interpreter most projects use; not a special variant.

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
# Multi-part RUN:
# 1) `apt-get update` → refresh the APT package index.
# 2) `apt-get install -y --no-install-recommends curl`
#    - curl: a command-line HTTP/URL client. Useful for health checks
#      (e.g., hitting http://localhost:8000/health) and quick diagnostics inside the container.
#    - `-y` auto-answers "yes" for non-interactive builds.
#    - `--no-install-recommends` avoids optional dependencies to keep the image small.
# 3) Remove cached package lists to shrink the layer.
# `&&` chains commands; if any step fails, the whole layer fails.

WORKDIR /app
# Sets the working directory *inside the image* for subsequent instructions and
# as the default CWD at container start.
# This does NOT create or mount a volume. Volumes/bind mounts are defined at
# runtime in docker-compose under `volumes:` and overlay this path when used.

COPY requirements.txt .
# Copy from build context (host) into the image at /app/requirements.txt.
# This is a build-time file copy (baked into the image), not a volume.
# Copying requirements first lets Docker cache the dependency-install layer so
# code-only changes don't force a full reinstall.

RUN pip install --no-cache-dir -r requirements.txt
# Install Python dependencies into the image.
# - `--no-cache-dir`: pip normally caches downloaded artifacts (sdists/wheels)
#   under ~/.cache/pip to speed future installs. This flag disables that cache,
#   reducing the final image size (packages are still installed; caches are not kept).
# - `-r requirements.txt`: read package names/versions from this file.

COPY app.py generator.py ./
# Copy application source files into the image at /app/.
# Done after dependency install so code changes only invalidate this layer
# (faster rebuilds via Docker layer caching).

ENV API_RATE_LIMIT_PER_MIN=300
# Define an environment variable inside the image/container.
# Here: default API rate limit (requests/min) used by the app to throttle clients
# or simulate upstream limits. Can be overridden via docker-compose `environment:`.

EXPOSE 8000
# Metadata: declares the container listens on TCP 8000.
# Does NOT publish the port externally by itself; publishing is done by
# docker-compose `ports: - "8000:8000"`.

CMD ["python", "app.py"]
# Default container command (can be overridden).
# Runs the app with the Python interpreter.
# vs ENTRYPOINT:
# - CMD supplies the default command/args (replaceable by `docker run ... <cmd>`).
# - ENTRYPOINT fixes the executable; CMD then supplies default args.

# Notes / hardening options (optional):
# - Create and run as a non-root user (RUN useradd -m appuser && chown -R appuser /app; USER appuser).
# - Add a .dockerignore to exclude venvs, caches, __pycache__, node_modules, etc.
# - Pin versions in requirements.txt for reproducible builds.
# - For Flask/FastAPI in production, prefer a WSGI/ASGI server:
#     CMD ["gunicorn","-b","0.0.0.0:8000","app:app"]
#   or:
#     CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
