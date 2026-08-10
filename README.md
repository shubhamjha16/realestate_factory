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
make test        # pytest, including the golden set, plus vitest
make golden      # replay the four golden cases and diff figure by figure
make lint
```

The golden set is four jobs — one per graph path — run with the LLM replaced by
a recorded cassette, compared on job type, section sequence, every computed
figure and the rendered document's hash. Figures are compared exactly; a paisa of
drift fails. See `backend/tests/golden/README.md`.

## Where this is

**S1 of 21 is complete**: the monorepo split, typed configuration, and the golden
harness that proves the split changed nothing. The engine still runs jobs the way
the prototype did — one process, `threading.Thread`, `jobs.json` — and there is
no database, no queue, no auth and no tenancy yet. Those are S2 through S5.

The plan, including what is structurally wrong today and the order it gets
fixed, is in `REALESTATE_FACTORY_SPRINTS.md`. `CLAUDE.md` is how to work in the
tree.
