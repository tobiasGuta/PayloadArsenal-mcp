# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.13.14-slim-bookworm@sha256:fcbd8dfc2605ba7c2eca646846c5e892b2931e41f6227985154a596f26ab8ed7

FROM ${PYTHON_IMAGE} AS collections
COPY config/collections.json /build/collections.json
COPY scripts/fetch_collections.py /build/fetch_collections.py
RUN python /build/fetch_collections.py /build/collections.json /opt/arsenal

FROM ${PYTHON_IMAGE} AS runtime

ENV ARSENAL_DIR=/opt/arsenal \
    ARSENAL_INDEX_PATH=/tmp/payload-arsenal-index.sqlite3 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --gid 10001 arsenal \
    && useradd --uid 10001 --gid arsenal --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin arsenal

WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.lock

COPY --from=collections --chown=root:root /opt/arsenal /opt/arsenal
COPY --chown=root:root server.py config.py schemas.py paths.py readers.py search.py categories.py wordlists.py indexing.py responses.py provenance.py references.py service.py ./
COPY --chown=root:root config/collections.json ./config/collections.json

RUN chmod -R a-w /app /opt/arsenal
USER 10001:10001

ENTRYPOINT ["python", "-u", "server.py"]
