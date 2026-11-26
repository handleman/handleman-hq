# Sandbox image for the swarm pilot (012 T17).
# Build from the factory root: docker build -f docker/Dockerfile -t swarm-sandbox .
# The container gets exactly one mount (`$PWD:/work`) at runtime; no HOME, SSH,
# or host caches are mounted unless explicitly opted in.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git nodejs npm openssh-client \
    && rm -rf /var/lib/apt/lists/*

# The harness is installed from its pyproject; the container mounts the target
# repo at /work and `hq` (or `python -m swarm.flow`) reads it via SWARM_TARGET.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install . && pip install pytest ruff mypy

# Run as an unprivileged user; sandbox.sh passes --user $(id -u):$(id -g) so
# files written into /work keep the host owner.
RUN useradd --create-home --uid 1000 swarm
USER swarm

WORKDIR /work
ENTRYPOINT ["python", "-m", "swarm.flow"]
