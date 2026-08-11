# Postgres 16 with PostGIS *and* pgvector.
#
# Neither official image has both: postgis/postgis ships PostGIS without vector,
# pgvector/pgvector ships vector without PostGIS. This repo needs both — geometry
# on properties and comparables from S2, and retrieval over the firm's own
# reporting corpus from S17 — so the image is built rather than pulled.
FROM postgis/postgis:16-3.4

ARG PGVECTOR_VERSION=v0.7.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        postgresql-server-dev-16 \
    && git clone --branch "${PGVECTOR_VERSION}" --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && make -C /tmp/pgvector \
    && make -C /tmp/pgvector install \
    && rm -rf /tmp/pgvector \
    && apt-get purge -y --auto-remove build-essential git postgresql-server-dev-16 \
    && rm -rf /var/lib/apt/lists/*

# Runs once, on an empty data directory. The migrations also create these, so a
# managed Postgres without this image still works — this only saves the first
# `alembic upgrade head` from needing superuser.
COPY init/01-extensions.sql /docker-entrypoint-initdb.d/01-extensions.sql
