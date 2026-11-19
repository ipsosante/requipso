ARG BASE_IMAGE=inseefrlab/onyxia-marimo-python:py3.12.13
FROM $BASE_IMAGE

LABEL maintainer="InseeFrLab <innovation@insee.fr>"

# The base image does not ship `uv` on PATH, so grab it from the official image.
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Some dependencies build native extensions from source (need a C/C++ toolchain)
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

USER 1000

WORKDIR /app
COPY . /app


# Install the current project (and its dependencies, incl. marimo) via uv
ENV UV_PROJECT_ENVIRONMENT="/opt/python/"
RUN uv sync --frozen --no-cache


EXPOSE 2718

# Runtime user (1000) can't write to ~/.cache/uv; use a temp cache instead.
ENV UV_NO_CACHE=1

# ENTRYPOINT is fixed; CMD holds the default (overridable) args forwarded to marimo.
# --no-sync: the environment is already built at /opt/python, don't re-sync at start.
ENTRYPOINT ["uv", "run", "--no-sync", "requipso"]
CMD ["--host", "0.0.0.0", "--port", "2718"]
