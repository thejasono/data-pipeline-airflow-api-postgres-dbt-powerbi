# ------------------------------------------------------------------------------
# Airflow image — pin exact Airflow + Python for reproducible builds
# ------------------------------------------------------------------------------

FROM apache/airflow:2.9.3-python3.11
# Base: Official Airflow image with Airflow 2.9.3 preinstalled on Python 3.11.
# Tag syntax = "<airflow-version>-python<major.minor>" → here: "2.9.3-python3.11".
# This tag selects the OS image built by the Airflow project that bundles Airflow
# and system deps for CPython 3.11. (You’re not specifying the host OS; you’re
# selecting the prebuilt base image by its tag.)

# ------------------------------------------------------------------------------
# System packages needed for operators/hooks and local builds
# ------------------------------------------------------------------------------

USER root
# The base image *defaults to running as* Linux user "airflow".
# `USER root` switches the current Linux user inside the image to root so we can
# install OS packages with apt.
#
# Clarifying Docker vs Compose terms:
# - Dockerfile `USER <name>` → the Linux account inside the image/container used to
#   run subsequent build steps and (unless changed later) the container at runtime.
# - docker-compose `build:` → path to the directory to build an image from (Dockerfile lives here).
# - docker-compose `image:` → name/tag to give the built image (e.g., "airflow-local").
# - docker-compose `container_name:` → name of the *running container instance*.
# These Compose fields do not create Linux users; they only control image naming
# and container runtime metadata. Linux users like `root`/`airflow` exist *inside*
# the image filesystem.

RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io docker-compose-plugin \
 && rm -rf /var/lib/apt/lists/*
# This RUN does not “start” the base image; it executes shell commands during the
# build to create a new image layer:
# 1) `apt-get update` → refresh Debian package index.
# 2) Install:
#    - `docker.io` → Docker CLI client binaries (useful if DAGs/operators call `docker`,
#      usually against a mounted /var/run/docker.sock).
#    - `docker-compose-plugin` → enables `docker compose` subcommand.
#    Flags: `-y` auto-yes; `--no-install-recommends` avoids optional deps → smaller layer.
# 3) Remove apt lists to shrink the image.
# Summary: refresh index → install docker tooling (minimal) → delete caches.

# ------------------------------------------------------------------------------
# Python dependencies (provider extras, hooks, custom libs)
# ------------------------------------------------------------------------------

COPY requirements.txt /requirements.txt
# Copy dependency manifest early so Docker can cache the subsequent pip install
# when only DAG code changes. This is a build-time copy (not a volume).

USER airflow
# Switch back to the non-root "airflow" user (best practice for running apps
# and installing Python packages). We used two Linux users:
# - root: privileged, used for apt installs during build.
# - airflow: unprivileged, default runtime user in the base image.

RUN export AIRFLOW_CONSTRAINTS_URL="https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.11.txt" \
    && python -m pip install --no-cache-dir psycopg2-binary -c "$AIRFLOW_CONSTRAINTS_URL" \
    && pip install --no-cache-dir -r /requirements.txt -c "$AIRFLOW_CONSTRAINTS_URL"
# Constraints file = a pinned list of versions known to be compatible with a
# specific Airflow + Python combo (here: Airflow 2.9.3, Python 3.11).
# Using `-c $AIRFLOW_CONSTRAINTS_URL` tells pip to resolve packages *within those pins*,
# preventing dependency conflicts with Airflow’s ecosystem.
#
# Breakdown:
# - Export URL to the official constraints for 2.9.3/3.11 (scoped to this RUN).
# - Install `psycopg2-binary` (prebuilt PostgreSQL driver wheels) under constraints.
# - Install your packages from requirements.txt under the same constraints.
# - `--no-cache-dir` avoids persisting pip’s wheel/download cache → smaller image.
# - `-r /requirements.txt` = read package requirements from that file.

# ------------------------------------------------------------------------------
# Runtime user and permissions
# ----------------------------------------------------------------------------
# For local dev convenience you may run as root to dodge permission issues on
# bind mounts (dags/, logs/, plugins/). For production, prefer the "airflow" user
# and fix ownership on mounted paths (e.g., chown/chmod) for least privilege.

USER root
#and why do we change the user back to this here, all the way at the end. Is it becuas ehte build is done and we only need to swtich to the airflow user during the image build, but now the image build is done we can go back to the user root