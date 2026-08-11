# Real Estate Factory

Valuation, compliance and transaction platform for Indian real estate. A React
console over a FastAPI engine: it ingests comparables, lease schedules,
construction stages and land records, computes valuations that are defensible,
and generates valuation reports, RERA filings and transaction documents where
**every figure traces to a comparable and every legal assertion to a document**.

Computation is deterministic and lives in Python. Drafting is a model's job, and
the model writes commentary *about* figures it never originates.

## Layout

```
backend/     FastAPI + LangGraph engine, Python 3.12, uv
frontend/    Vite + React 19 + TypeScript console, yarn
packages/    api-types — generated from the backend's OpenAPI spec (S3)
```

## Getting started

```bash
make install                       # uv sync + yarn install
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# set GROQ_API_KEY in backend/.env — the engine will not boot without it
make dev                           # postgis + redis + API :8004 + console :5173
```

Requires Python 3.12 (via `uv`), Node 20+, yarn and Docker.

## Verifying

```bash
make test        # pytest, including the golden set, plus vitest — no database needed
make test-db     # repository tests against a live PostGIS (needs `make infra`)
make golden      # replay the four golden cases and diff figure by figure
make lint        # ruff + eslint + the money-column guard
make schema-sql  # render the whole schema as DDL without touching a database
```

The golden set is four jobs — one per graph path — run with the LLM replaced by
a recorded cassette, compared on job type, section sequence, every computed
figure and the rendered document's hash. Figures are compared exactly; a paisa of
drift fails. See `backend/tests/golden/README.md`.

## Where this is

**S3 of 21 is complete.**

- **S1** — the monorepo split, typed configuration, and the golden harness that
  proves the split changed nothing.
- **S2** — Postgres + PostGIS with a hand-written GiST index, Alembic, and the
  end of `jobs.json`: a job interrupted mid-graph is now a row someone can find
  rather than a record that never existed. Once a job is terminal, the
  repository refuses to change its status.
- **S3** — layered HTTP with route handlers under 15 lines and no SQL, request
  validation that answers 422 naming the field and listing what was acceptable,
  and `packages/api-types` generated from the OpenAPI spec with a CI gate that
  fails on drift.

Still ahead before anything real runs through it: **S4** replaces
`threading.Thread` with arq, and **S5** adds auth, firms, mandates and tenancy.
Until S5, every caller can read every job — and jobs carry client transaction and
title data.

The plan, including what is structurally wrong today and the order it gets
fixed, is in `REALESTATE_FACTORY_SPRINTS.md`. `CLAUDE.md` is how to work in the
tree.
