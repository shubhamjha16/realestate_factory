-- Extensions the schema depends on, created before the first migration runs.
-- Alembic's autogenerate does not create these and will not remind you.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Retrieval over the firm's own reporting corpus, scoped per firm — S17.
-- Available because docker/postgres/Dockerfile builds pgvector into the image.
CREATE EXTENSION IF NOT EXISTS vector;
