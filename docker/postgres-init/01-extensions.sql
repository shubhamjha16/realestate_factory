-- Extensions the schema depends on, created before the first migration runs.
-- Alembic's autogenerate does not create these and will not remind you.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- pgvector is used from S17 for retrieval over the firm's own reporting corpus.
-- The postgis image does not ship it, so the extension is not created here; S17
-- either swaps this image for one carrying both, or installs it in a Dockerfile.
