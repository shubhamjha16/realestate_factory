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
make worker      # run the arq worker against the local Redis
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

**Tenancy.** Every repository function takes a `FirmScope` and filters by it.
`tests/test_repository_scope_guard.py` fails the build if one does not, so the
rule is structural rather than a review item. Six functions are exempt, each
listed in `UNSCOPED_BY_DESIGN` with the reason there is no session to scope by.
A cross-firm read answers **404, never 403** — "you may not read this" confirms
the row exists, and for a mandate name or a property address that confirmation
is the leak. The firm comes from a signed token; no endpoint accepts a firm id.

**Queue.** The web process writes a job row and enqueues; the arq worker runs
the graph. Tasks are written to be safe to run twice, because at-least-once is
what a queue gives you — `run_generation` claims the job first and leaves a
terminal one alone.

## Things to know before you change something

- **`PYTHONHASHSEED=0` is required to run the tests.** `intake_node` builds its
  prompt by joining a set, so the prompt text differs between processes and the
  golden cassettes stop matching. `make test` sets it. S10 split the graph but
  left `intake_node`'s set join in place, so this is still required.
- **The golden set is the regression net.** Four cases, one per graph path, with
  the LLM replaced by a cassette. Figures are compared exactly — a paisa of drift
  fails. If a prompt change is intended, `make golden-record` re-records it and
  the diff goes in the commit.
- **`services/valuation/` is pure and deterministic.** No LLM call belongs in it,
  now or later.
- **Money is parsed from strings and never from floats.** `to_decimal` raises on
  a float rather than laundering imprecision it cannot undo. Round once, at the
  boundary; intermediate rounding is how a rent roll stops tying to its lines.
- **`packages/units/units.json` is the only place a conversion factor lives.**
  Both apps read it. The state-dependent factors (bigha, biswa, katha, vigha) are
  seeded `verified: false` from commonly cited values and **refuse to be used
  without an explicit opt-in** — verifying them against notified schedules is
  §11.2, still unassigned.
- **The evidence gate has no bypass.** `validators/evidenceValidator.enforce`
  takes no `force`, `allow_missing` or `strict` parameter, and a test asserts
  that by inspecting its signature. Adding one would change what this product is.
- **Approaches are reconciled, never averaged.** Weights sum to 1, each carries a
  rationale, and approaches that diverge beyond the threshold are refused rather
  than split down the middle.
- **The trimmed mean is a sanity statistic, not a conclusion.** It survives as
  `trimmed_mean_rate_sanity_only`. Nothing in the codebase returns a key a caller
  could mistake for a value conclusion.
- **`Base` lives in `app/models/base.py`, not `configs/dbConfig.py`.** Reading the
  schema — autogenerate, the money-column guard — must not require a database URL
  or a provider key.
- **The money-column guard is load-bearing.** It now covers 7 real monetary
  columns across the comparables, encumbrance and valuation tables, in the models
  by type and in the migrations by text. Adding an amount is how you find out.
- **`JWT_SECRET` has no default.** A shipped default means anyone who reads this
  repository can mint a token for any firm. Boot fails naming it, like
  `GROQ_API_KEY`.
- **MFA is on by default** (`MFA_REQUIRED=true`). §11.1 is settled as IBBI and
  bank panel valuation, so these accounts sign documents a bank or a tribunal
  relies on. Turning it off is a deliberate act with a name.
- **The bearer token is held in memory, never localStorage.** A token that
  survives a tab close is one any script on the page can read.
- **The reconciliation path and the trimmed-mean outlier handling are the two
  best things in the original prototype.** Protect both. (The trimmed mean stays
  only as a pre-adjustment sanity statistic from S7 — never as a value
  conclusion.)

## Open decisions

§11 of the sprint plan lists three. Two are still open and have deadlines:

1. **Which regulated basis** — **settled: IBBI-registered valuation (IBC and
   Companies Act) and bank panel valuation.** A `valuer` account cannot exist
   without `ibbi_reg_no` and an asset class, only a partner or a registered
   valuer may sign, S8's evidence gate has no bypass, and S13 checks the
   registration covers the asset class.
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
| S4 | Real queue: arq + Redis | done |
| S5 | Auth, firms, mandates, tenancy | done |
| S6 | Decimal migration, units, parser hardening | done |
| S7 | The comparable adjustment grid | done |
| S8 | The evidence gate | done |
| S9 | Three approaches and their reconciliation | done |
| S10 | Split `re_graph.py` + golden-set harness | done — 16 fixtures, all four paths |
| S11 | Renderer hardening + model routing + cost ledger | done — the ledger has no table yet |
| S12 | Provenance, documents, audit trail | code complete — **no migration** |
| S13 | Review notes, sign-off, encryption, retention | code complete — **no migration** |
| S14 | RERA, approvals, statutory compliance | done |
| S15 | Report depth and export breadth | done |
| S16 | Portfolio, rent roll, client view | done |
| S17 | Firm-scoped retrieval | partial — in-memory corpus, no pgvector |
| S18 | Webhooks, SSE, quotas | partial — signing real, SSE scripted |
| S19 | Observability, testing, CI/CD | partial — no Playwright critical path |
| S20 | Security, confidentiality, retention | done |
| S21 | Load, cost, closed beta | partial — synthetic harness, no beta cohort |

The unadjusted mean is gone. A valuation now comes from an adjustment grid where
every comparable carries a written rationale per factor, and the sample is
refused if it is too small, too old, too far away, or still disagrees after
adjustment.

**The gaps that will bite you are in the README's "Known gaps" section.** The one
to read first: five tables — `deliverables`, `deliverable_versions`,
`deliverable_sections`, `review_notes`, `audit_events` — are declared on
`Base.metadata` but no Alembic revision creates them. `alembic upgrade head`
yields a database where S12's provenance chain and S13's review and sign-off
cannot run. Their live-DB tests skip without `TEST_DATABASE_URL` and the CI
database job does not reach them, which is why it survived. `cost_entries`,
`webhook_deliveries` and `node_runs` have no model at all.

**Four exit proofs cannot be met in code**, each of which asks for a person: S7's
"an IBBI-registered valuer reviews one full grid and signs it", S9's "a valuer
compares the reconciled figure against their own manual working", S14's RERA
practitioner review and S15's reporting-checklist review. The arithmetic is built
and tested; the professional review is not something the repository can do to
itself.
