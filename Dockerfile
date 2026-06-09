# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14.5
ARG ALPINE_VERSION=3.23

# ── base: shared Poetry install + dependency layer ────────────────────────────
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS base

WORKDIR /app

RUN apk add --update curl && rm -rf /var/cache/apk/*

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock* /app/

RUN poetry lock && poetry install --no-root && \
    # Patch build tooling shipped in the image (CVE-2026-24049 in wheel, etc.).
    pip install --no-cache-dir --upgrade pip setuptools wheel

COPY ./alembic.ini /app
COPY ./alembic/ /app/alembic/

# ── app: full application ─────────────────────────────────────────────────────
FROM base AS app

COPY ./incidentbot /app/incidentbot
COPY ./main.py /app
COPY ./entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Bake the build-time version string into the image.
# Set via --build-arg APP_VERSION=... in CI; defaults to "dev" for local builds.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# Build metadata labels. The benefex/docker orb passes these build args and then
# locates the pushed image to capture its digest via
#   docker images -f "label=io.benefexapps.commit-id=<sha>"
# so the commit-id label is required for the deploy step (otherwise docker-url
# is empty and the build fails).
ARG BUILD_DATE
ARG BUILD_URL
ARG COMMIT_ID
LABEL io.benefexapps.build-date=$BUILD_DATE
LABEL io.benefexapps.build-url=$BUILD_URL
LABEL io.benefexapps.commit-id=$COMMIT_ID

CMD ["/app/entrypoint.sh"]
