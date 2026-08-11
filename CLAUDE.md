# Real Estate Factory — working notes

A property system of record: valuations, RERA filings and transaction documents
where every figure traces to a comparable and every legal assertion to a
document. One repository, two apps. `REALESTATE_FACTORY_SPRINTS.md` is the plan;
this file is how to work in the tree.

## Layout

```
backend/     FastAPI + LangGraph engine   (mirrors ai-chat-be)
frontend/    Vite + React 19 console      (mirrors etl-student-frontend)
packages/    api-types — generated from OpenAPI in CI (S3)
```

## Commands

```bash
make install     # uv sync + yarn install
make dev         # postgis + redis + API :8004 + console :5173
make test        # pytest (incl. the golden set) + vitest — no database needed
make test-db     # repository tests against a live PostGIS
make golden      # replay the golden set and diff against expected/
make api-types   # regenerate packages/api-types from the OpenAPI spec
make lint        # ruff + eslint + the money-column guard
make migrate     # alembic upgrade head
make schema-sql  # render the whole schema as DDL without touching a database
```

`make help` lists everything.

## The rules that are not negotiable

These are what the product is, not style preferences. Each is enforced
structurally in the sprint named, never by prompt instruction.

- **The model never produces a number.** Figures come from `valuation_lines` or
  they do not render (S11).
- **The model never asserts a fact about title.** Ownership, tenure, encumbrance
  and approvals resolve to a document or the render blocks (S8). No bypass flag.
- **An unadjusted mean is not a valuation.** Every comparable carries its
  adjustments and a written rationale (S7).
- **Approaches are reconciled, never averaged blindly.** Weights sum to 1 and
  each carries a rationale (S9).
- **`Decimal` everywhere, one unit table.** No `float` touches money. sqft/sqm/
  bigha conversion comes from a single shared source used by both apps (S6).
- **Nothing is dropped silently.** parsed + rejected + duplicate must equal input
  rows, and the rejected list is visible in the console (S6).
- **Tenancy is enforced at the repository layer**, never the router (S5).
- **Location and ownership are sensitive.** Exact coordinates, owner names and
  survey numbers stay out of logs and out of client-role responses.
- **The output is a draft** until a registered valuer signs it (S13).

## Conventions

**Backend.** Layered: `routers/` → `controllers/` → `services/` → `repositories/`.
Route handlers under 15 lines, no SQL. Every environment read goes through
`configs/envConfig.py`; a missing required variable is a boot failure that names
it. File naming is camelCase to match `ai-chat-be`.

**Frontend.** Feature-first. A feature imports freely from `components/`,
`global/`, `hooks/`, `shared/`, `store/` and `utils/` — and from another feature
**only through its `index.ts`** (lint-enforced). Server state lives in TanStack
Query; Zustand holds only what the user is doing right now. Money is a decimal
string and the console never does arithmetic on it.

**Migrations.** One revision per logical change, always hand-reviewed.
Autogenerate does not emit PostGIS GiST indexes on `geom`, and it will happily
type a money column as `Float`. `make migration m="..."` prints the checklist,
`scripts/check_money_columns.py` fails the build on the second, and
`make schema-sql` shows you the DDL a revision actually produces.

**Job finality.** Once `jobs.terminal_at` is set, `jobRepository` refuses any
further write to `status`. It is at the repository layer because there will be
several writers — the web process, S4's worker, S13's retention sweep — and a
rule enforced in one caller is a rule the next caller does not know about.

**Types are generated, not mirrored.** `packages/api-types` comes from the
backend's OpenAPI spec. Change a schema, run `make api-types`, commit the
result — CI regenerates and diffs, so stale types fail the build.

## Things to know before you change something

- **`PYTHONHASHSEED=0` is required to run the tests.** `intake_node` builds its
  prompt by joining a set, so the prompt text differs between processes and the
  golden cassettes stop matching. `make test` sets it. S10 fixes the cause.
- **The golden set is the regression net.** Four cases, one per graph path, with
  the LLM replaced by a cassette. Figures are compared exactly — a paisa of drift
  fails. If a prompt change is intended, `make golden-record` re-records it and
  the diff goes in the commit.
- **`services/valuation/` is pure and deterministic.** No LLM call belongs in it,
  now or later.
- **`Base` lives in `app/models/base.py`, not `configs/dbConfig.py`.** Reading the
  schema — autogenerate, the money-column guard — must not require a database URL
  or a provider key.
- **The money-column guard currently checks zero real columns.** Nothing in the
  first migration is monetary. It is proven against synthetic fixtures and
  becomes load-bearing at S6/S7, when `Decimal` and the adjustment grid land.
- **The reconciliation path and the trimmed-mean outlier handling are the two
  best things in the original prototype.** Protect both. (The trimmed mean stays
  only as a pre-adjustment sanity statistic from S7 — never as a value
  conclusion.)

## Open decisions

§11 of the sprint plan lists three. Two are still open and have deadlines:

1. **Which regulated basis** — IBBI/IBC, bank panel, or developer feasibility.
   The sign-off model follows from it. **Decide before S5.**
2. **Who maintains jurisdictional data** — RERA rules, stamp duty, circle rates,
   unit conventions. A standing cost with an owner and a review cadence.
   **Decide before S14.**
3. `repositories` vs `respositories` — **settled**: correct spelling, here and
   from now on. `ai-chat-be` has the typo; this repo does not copy it.

## Sprint status

| | Sprint | State |
|---|---|---|
| S1 | Monorepo split + typed config | done |
| S2 | Postgres + PostGIS, Alembic, death of `jobs.json` | done — live-DB proofs run in CI |
| S3 | Layered HTTP + generated API types | done |
| S4 | arq + Redis | next |

S2 and S3 are the last sprints before tenancy. Until S5 lands, every caller can
read every job, and jobs carry client transaction and title data — so nothing
real should go through this deployment yet.
