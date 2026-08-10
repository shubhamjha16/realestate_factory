# Real Estate Factory — Valuation, Compliance & Transaction Platform
### Technical specification + 21-sprint build plan

> Goal: turn the current 7-file flat prototype into a production monorepo — a React console over a FastAPI engine — that ingests comparables, lease schedules, construction stages and land records, computes valuations that are defensible, and generates valuation reports, RERA filings and transaction documents where **every figure traces to a comparable and every legal assertion to a document**.
>
> **One repository, two apps.** `backend/` mirrors `ai-chat-be`. `frontend/` mirrors `etl-student-frontend`. Structure lands before features.

---

## 0. What this product is

**A property system of record.** Every property, title document, comparable, lease, construction milestone, valuation and generated deliverable lives in a mandate — versioned, permissioned, audited, retained on a policy. Valuations persist across dates, so a property valued in March and revalued in September is one asset with a history and an explainable delta.

**A computation engine that is deterministic, and a drafting engine that is not.** Comparable analysis, rent rolls, NOI, cap rates, GDV and disbursement schedules are computed in Python and never touched by a model. The model writes *commentary about* those figures. A valuation figure invented in prose is the failure this separation exists to prevent.

**A console the valuer actually works in.** Add a property, upload comparables, adjust them for size, age, floor and frontage, see the derived rate, review the valuation, sign off, export. The engine without the console is a curl endpoint.

**The professional-liability posture is the product.** In India a valuation report for most regulated purposes must be signed by an IBBI-registered valuer, and a bank, a court or a resolution professional relies on it. A wrong figure, or a title assertion with no document behind it, is a professional-conduct matter for the signer. That drives the adjustment audit trail (S7), the evidence gate (S8) and the sign-off gate (S13).

---

## 1. Where this repo actually is today

Eight files, 1,509 lines, flat. No `app/` package, no frontend, no DB, no migrations, no tests, no CI, no deploy config, no auth.

```
realestate_factory/               # CURRENT (flat, backend only)
├── re_graph.py            686 loc   16-node LangGraph, four paths
├── valuation_calculator.py 214 loc   comparables · yield · cap rate · GDV · NOI
│                                     · rent roll · construction · portfolio
├── re_renderer.py         202 loc   python-docx renderers
├── property_data_parser.py 164 loc   comparables · leases · stages · portfolio · land
├── api_bridge.py          154 loc   FastAPI + threading + jobs.json
├── config.py               55 loc   module-level os.environ reads
├── uploader.py             34 loc
└── requirements.txt · .env.example
```

What works and must not regress:

| Asset | State |
|---|---|
| **Four-path graph** | `valuation` (iterative section drafter) · `compliance` (structure→critic→drafter) · `agreement` (single-shot) · `reconciliation` (deterministic, zero LLM) |
| **16 nodes** | intake · property_data_parser · valuation_calculator · research · vision · rec_renderer · valuation_structure · valuation_critic · section_drafter · compliance_structure · compliance_critic · compliance_drafter · agreement_drafter · renderer · healer · upload |
| **16 job types** | 3 valuation · 5 compliance · 6 agreement · 2 reconciliation |
| **Real computation** | comparable analysis with outlier trimming, market value, rental yield, cap rate, GDV, NOI, rent roll with escalations, construction disbursement, portfolio |
| **Input formats** | comparable sales, lease schedules, construction stages, portfolio, land records |
| **Critic + healer loops** | `MAX_CRITIC_RETRIES=2`, `MAX_HEALER_RETRIES=2` |

The deterministic reconciliation path and the trimmed-mean outlier handling in `analyse_comparables` are the two best decisions in this repo. Protect both.

What is structurally wrong, in order of severity:

1. **Comparables are averaged, not adjusted.** `analyse_comparables` takes a trimmed mean of raw price-per-sqft and calls it `suggested_rate`. Actual valuation practice adjusts each comparable for size, age, floor, frontage, view, condition, transaction date and distress before averaging. **An unadjusted mean is not a valuation**, and a report that presents one as though it were is the single biggest professional exposure in this repo.
2. **No adjustment audit trail.** There is nowhere to record why a comparable was weighted, discounted or rejected — which is exactly what a reviewer, a bank or a tribunal asks to see.
3. **Money is `float`.** Property values run to crores; `round(area * rate, 2)` on binary floats produces figures that will not reconcile across a portfolio, and a rent roll that should tie will not.
4. **Only the sales-comparison approach exists.** No income capitalisation as a first-class method (NOI and cap rate exist but are not wired to a value conclusion), no cost/DRC approach, and **no reconciliation between approaches** — which is the step that produces a defensible final figure.
5. **No tenancy of any kind.** No firm, no user, no mandate. Every caller reads every job — and jobs contain client transaction and title data.
6. **`jobs.json` + `threading.Thread`.** Restart loses the job; there is no queue.
7. **The parser fails silently.** Unrecognised input yields an empty structure, and a valuation over zero comparables renders successfully.
8. **No frontend exists.** The product is a `curl` endpoint.

---

## 2. Locked tech stack

| Concern | Choice | Notes |
|---|---|---|
| **Monorepo tooling** | yarn workspaces + `Makefile` | one `make dev` brings up both apps |
| Backend runtime | Python 3.12 | `.python-version` pinned |
| Backend framework | FastAPI (async) | already present, keep |
| Backend packaging | **uv** | `pyproject.toml` + `uv.lock`; `requirements.txt` generated |
| ORM / migrations | SQLAlchemy 2.0 (async) + **Alembic** | same as ai-chat-be |
| DB | Postgres 16 + **PostGIS** + pgvector (S17) | properties have geometry, not just addresses |
| Money type | **`Decimal`**, `NUMERIC(18,2)` | non-negotiable; see S6 |
| Cache / queue | Redis + **arq** | replaces `threading.Thread` |
| Agent framework | **LangGraph** | decomposed, not replaced |
| Router LLM | Groq `llama-3.3-70b-versatile` | intake, classification, cheap checks |
| Drafter LLM | Claude Sonnet-class | structure, section drafting, critic |
| Documents | `pypdf` + OCR (`eng`+`hin`) | title deeds and approvals are scans |
| Rendering | python-docx → DOCX; LibreOffice → PDF; **XLSX rent roll** (S15) | |
| Storage | S3 `ap-south-1`, presigned only, SSE-KMS | title documents and photographs |
| Frontend | **Vite + React 19 + TypeScript**, **yarn** | mirrors etl-student-frontend |
| Frontend state | Zustand + TanStack Query | server state is not client state |
| Maps | MapLibre + OSM tiles | comparables are a map problem before a table problem |
| Deploy | Render (api + worker) · Vercel (console) | |
| CI | GitHub Actions, **path-filtered** | backend and frontend run independently |

---

## 3. Monorepo layout

```
realestate_factory/
├── backend/                          # ← mirrors ai-chat-be
│   ├── alembic/
│   │   ├── versions/  env.py  script.py.mako
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── configs/
│   │   │   ├── envConfig.py          # pydantic-settings, fail-fast, typed
│   │   │   ├── dbConfig.py           # async_engine, sessionmaker, get_db
│   │   │   ├── jobTypes.py           # VALUATION_/COMPLIANCE_/AGREEMENT_/RECONCILIATION
│   │   │   ├── sourceConfig.py       # input format registry + schema versions
│   │   │   └── jurisdictionConfig.py # state RERA rules, stamp duty, circle rates
│   │   ├── controllers/
│   │   │   ├── authController.py      clientController.py
│   │   │   ├── mandateController.py   propertyController.py
│   │   │   ├── comparableController.py  valuationController.py
│   │   │   ├── leaseController.py     complianceController.py
│   │   │   ├── generationController.py  reviewController.py
│   │   │   └── usageController.py
│   │   ├── models/
│   │   │   ├── firm.py  user.py  client.py  mandate.py
│   │   │   ├── property.py  parcel.py  unit.py  propertyDocument.py
│   │   │   ├── comparable.py  comparableAdjustment.py
│   │   │   ├── valuation.py  valuationApproach.py  valuationLine.py
│   │   │   ├── lease.py  leaseEscalation.py  rentRollLine.py
│   │   │   ├── constructionStage.py  disbursement.py
│   │   │   ├── reraProject.py  reraFiling.py  approval.py
│   │   │   ├── encumbrance.py  titleChainEntry.py
│   │   │   ├── deliverable.py  deliverableVersion.py  deliverableSection.py
│   │   │   ├── job.py  nodeRun.py  costEntry.py
│   │   │   ├── permission.py  auditEvent.py
│   │   │   ├── webhookDelivery.py  usageCounter.py
│   │   ├── repositories/             # ← ai-chat-be spells this `respositories`; §11
│   │   │   ├── jobRepository.py        propertyRepository.py
│   │   │   ├── comparableRepository.py  valuationRepository.py
│   │   │   ├── leaseRepository.py       mandateRepository.py
│   │   │   ├── deliverableRepository.py  userRepository.py
│   │   ├── routers/
│   │   │   ├── __init__.py           # aggregates under /api/v1
│   │   │   ├── health.py  auth.py  clients.py  mandates.py
│   │   │   ├── properties.py  documents.py  comparables.py
│   │   │   ├── valuations.py  leases.py  construction.py
│   │   │   ├── rera.py  generation.py  jobs.py  deliverables.py
│   │   │   ├── review.py  audit.py  usage.py  webhooks.py
│   │   ├── schemas/
│   │   │   ├── request/              # generateRequest, comparableRequest, adjustmentRequest
│   │   │   └── response/             # jobResponse, valuationResponse, rentRollResponse
│   │   ├── services/
│   │   │   ├── generationService.py
│   │   │   ├── graph/
│   │   │   │   ├── builder.py  state.py  routes.py
│   │   │   │   ├── nodes/
│   │   │   │   │   ├── intake.py  propertyDataParser.py  valuationCalculator.py
│   │   │   │   │   ├── research.py  vision.py  evidenceCheck.py
│   │   │   │   │   ├── recRenderer.py
│   │   │   │   │   ├── valuationStructure.py  valuationCritic.py  sectionDrafter.py
│   │   │   │   │   ├── complianceStructure.py  complianceCritic.py
│   │   │   │   │   ├── complianceDrafter.py  agreementDrafter.py
│   │   │   │   │   ├── renderer.py  healer.py  upload.py
│   │   │   │   └── prompts/          # prompts are data, one module per node
│   │   │   ├── ingest/
│   │   │   │   ├── detect.py         # explicit, caller-overridable
│   │   │   │   ├── parsers/  comparables.py  leaseSchedule.py
│   │   │   │   │            constructionStages.py  portfolio.py  landRecords.py
│   │   │   │   ├── documents/  pdf.py  ocr.py  titleExtract.py
│   │   │   │   ├── schemas/          # per-format expected shape + version
│   │   │   │   ├── normalize.py  dedupe.py  geocode.py
│   │   │   ├── valuation/            # ← pure, deterministic, NO LLM, Decimal only
│   │   │   │   ├── money.py          # Decimal helpers, rounding policy
│   │   │   │   ├── adjust.py         # ★ per-comparable adjustment grid (S7)
│   │   │   │   ├── salesComparison.py
│   │   │   │   ├── incomeApproach.py # NOI, cap rate, DCF
│   │   │   │   ├── costApproach.py   # replacement cost less depreciation
│   │   │   │   ├── reconcile.py      # ★ weighted reconciliation of approaches (S9)
│   │   │   │   ├── rentRoll.py  escalation.py  wault.py
│   │   │   │   ├── construction.py   # stage-wise disbursement
│   │   │   │   └── portfolio.py
│   │   │   ├── compliance/
│   │   │   │   ├── rera.py           # state-wise rules, quarterly obligations
│   │   │   │   ├── stampDuty.py      # state-wise rates, circle-rate floor
│   │   │   │   └── checklists.py
│   │   │   ├── render/
│   │   │   │   ├── docxRenderer.py  clauseRegistry.py  clauses/
│   │   │   │   └── exporters/  docx.py  pdf.py  xlsx.py  json.py
│   │   │   ├── llm/  router.py  groqClient.py  anthropicClient.py  ledger.py
│   │   │   ├── access/  authz.py  audit.py
│   │   │   └── webhookService.py     # HMAC-signed delivery + backoff
│   │   ├── utils/
│   │   │   ├── logger.py  redaction.py  idempotency.py
│   │   │   ├── hashing.py  geo.py  retry.py  redisClient.py
│   │   ├── validators/
│   │   │   ├── generateValidator.py  ingestValidator.py
│   │   │   ├── comparableValidator.py    # ★ sample adequacy (S7)
│   │   │   ├── evidenceValidator.py      # ★ no unsourced assertion (S8)
│   │   │   ├── figureProvenanceValidator.py  # ★ no model-invented number (S11)
│   │   │   └── clausePlanValidator.py
│   │   ├── workers/
│   │   │   ├── arqApp.py
│   │   │   └── tasks.py              # run_generation, ingest_data, ocr_document,
│   │   │                             # deliver_webhook, retention_sweep
│   │   └── main.py                   # create_app()
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── fixtures/imports/         # real comparable sets, rent rolls, stage schedules
│   │   ├── fixtures/valuations/      # valuer-reviewed worked examples
│   │   ├── golden/                   # 16 job-type fixtures + expected structure
│   │   ├── test_parsers.py  test_adjust.py  test_approaches.py
│   │   ├── test_evidence.py  test_authz.py  test_generation_e2e.py
│   ├── .env.example  .python-version
│   ├── main.py  pyproject.toml  uv.lock  requirements.txt
│
├── frontend/                         # ← mirrors etl-student-frontend file-for-file
│   ├── public/
│   ├── src/
│   │   ├── components/               # shared, presentational only
│   │   │   ├── ui/       Button · Input · Modal · Toast · Skeleton · DataGrid · Tabs
│   │   │   ├── feedback/ ErrorBoundary · EmptyState · ErrorState
│   │   │   └── property/ MapView · ComparableCard · AdjustmentGrid
│   │   │                 · ValueRangeBar · RentRollTable
│   │   ├── features/                 # feature-first, boundary lint-enforced
│   │   │   ├── auth/     components/ hooks/ services/ store.ts types.ts index.ts
│   │   │   ├── clients/       mandates/        properties/
│   │   │   ├── documents/     comparables/     valuations/
│   │   │   ├── leases/        construction/    rera/
│   │   │   ├── deliverables/  review/  dashboard/  usage/
│   │   ├── global/
│   │   │   ├── apiClient.ts          # auth header · retry · SSE · error mapping
│   │   │   ├── errors.ts  env.ts
│   │   ├── hooks/
│   │   │   ├── useDebounce.ts  useInterval.ts  useMediaQuery.ts
│   │   ├── layouts/
│   │   │   ├── AppLayout.tsx  MandateLayout.tsx  AuthLayout.tsx
│   │   ├── router/
│   │   │   ├── index.tsx             # lazy() per route
│   │   │   ├── routes.ts  guards.tsx
│   │   ├── shared/constants/
│   │   │   ├── jobTypes.ts           # mirrors backend configs/jobTypes.py
│   │   │   ├── propertyTypes.ts  states.ts  adjustmentFactors.ts
│   │   │   ├── routes.ts  roles.ts
│   │   ├── store/
│   │   │   ├── sessionStore.ts  uiStore.ts
│   │   ├── utils/
│   │   │   ├── format.ts             # ₹ lakh/crore, sqft/sqm, never toFixed on money
│   │   │   ├── money.ts  area.ts  download.ts  redactDisplay.ts
│   │   ├── App.tsx  main.tsx  index.css  vite-env.d.ts
│   ├── tests/                        # Vitest + RTL · Playwright e2e (S19)
│   ├── .env.example  .gitignore  CLAUDE.md  README.md
│   ├── eslint.config.js  index.html  package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json  tsconfig.app.json  tsconfig.node.json
│   ├── vercel.json  vite.config.ts  yarn.lock
│
├── packages/
│   └── api-types/                    # OpenAPI → TS types, generated (S3)
│
├── .github/workflows/                # path-filtered: backend.yml · frontend.yml
├── docker-compose.yml                # postgres+postgis + redis for local dev
├── Makefile                          # make dev · make test · make migrate
├── CLAUDE.md  README.md  .gitignore  package.json  yarn.lock  render.yaml
```

**Both apps mirror an existing house repo, deliberately.**

`backend/` is `ai-chat-be`: `alembic/` + `alembic.ini` beside `app/`, and inside `app/` the same nine directories — `configs`, `controllers`, `models`, `repositories`, `routers`, `schemas/request`, `services`, `utils`, `validators` — plus a top-level `main.py`, `pyproject.toml`, `uv.lock`, `requirements.txt`, `.env.local`, `.python-version`, `render.yaml`.

`frontend/` is `etl-student-frontend`: `public/` + `src/` with the same directories — `components`, `features`, `global`, `hooks`, `layouts`, `router`, `shared/constants`, `store`, `utils` — and the same root files: `.env.example`, `.gitignore`, `CLAUDE.md`, `README.md`, `eslint.config.js`, `index.html`, `package.json`, `tailwind.config.js`, the `tsconfig` trio, `vercel.json`, `vite.config.ts`, `yarn.lock`. Same yarn, same Vercel target.

Two intentional departures, both consequences of what this app is:

- **`components/property/`** — the map, comparable cards, the adjustment grid and the value-range bar are rendered by five features. Comparables are a map problem before they are a table problem, so the map belongs in shared components rather than inside one feature.
- **`utils/area.ts`** alongside `money.ts` — the etl frontend never converts units. Here, sqft ↔ sqm ↔ acre ↔ guntha ↔ bigha conversions differ by state and a wrong conversion silently multiplies a valuation. Unit handling is a first-class utility with its own tests.

**Why a monorepo here.** Adjustment factors, property types, unit conventions and rounding policy must match backend and frontend exactly. A console that converts sqm differently from the engine produces a report whose area and rate contradict its total. `packages/api-types` is generated from the backend's OpenAPI spec in CI, so a schema change that breaks the console **fails the build**.

**Boundary rule** (lint-enforced, S9): a feature imports freely from `components/`, `global/`, `hooks/`, `shared/`, `store/`, `utils/` — and from another feature **only through its `index.ts`**.

---

## 4. Data model (Postgres + PostGIS + Alembic)

Every monetary column is `NUMERIC(18,2)`. There is no `float8` for money in this schema.

```
firms               id, name, plan, seats, created_at
users               id, firm_id, email, hashed_password, google_sub,
                    role(partner|valuer|analyst|readonly|client),
                    ibbi_reg_no?, valuer_asset_class?, mfa_enabled
clients             id, firm_id, name, kind(bank|developer|nbfc|fund|individual)
mandates            id, firm_id, client_id, kind(valuation|due_diligence|
                    rera|transaction|portfolio),
                    purpose(loan|ibc|dispute|financial_reporting|internal),
                    instructed_on, due_on, status, valuer_id, created_at
                    -- purpose drives the required basis of value; S9

properties          id, firm_id, mandate_id?, title, property_type,
                    address, locality, city, state, pincode,
                    geom geography(Point,4326), survey_no, khasra_no,
                    land_area NUMERIC, land_area_unit,
                    built_up_area NUMERIC, carpet_area NUMERIC,
                    year_built, floors, tenure(freehold|leasehold), created_at
parcels             id, property_id, survey_no, area NUMERIC, geom geography
units               id, property_id, unit_no, floor, carpet_area NUMERIC,
                    saleable_area NUMERIC, status(vacant|let|sold)
property_documents  id, property_id, kind(title_deed|mutation|approval|
                    encumbrance_cert|tax_receipt|photo|plan),
                    s3_key, doc_date, issuing_authority, ocr_text_s3_key,
                    verified_by?, verified_at?, created_at
title_chain_entries id, property_id, ord, from_party, to_party,
                    instrument, registered_on, reg_no, document_id?
encumbrances        id, property_id, kind(mortgage|lien|litigation|lease),
                    holder, amount NUMERIC?, from_date, to_date?, document_id?

comparables         id, property_id, source, address, geom geography,
                    sale_date, sale_price NUMERIC, area NUMERIC, area_unit,
                    rate_per_unit NUMERIC, property_type, age_years,
                    floor, distance_m, verified(bool), verified_by?, note
comparable_adjustments  id, comparable_id,
                    factor(size|age|floor|frontage|view|condition|
                           time|location|distress|tenure),
                    pct NUMERIC, rationale, applied_by, created_at
                    -- ★ this table IS the valuation's defensibility; S7

valuations          id, property_id, mandate_id, valuation_date,
                    basis(market|fair|liquidation|distress|insurable),
                    premise(existing_use|highest_best_use),
                    concluded_value NUMERIC, value_range_low NUMERIC,
                    value_range_high NUMERIC, currency,
                    status(draft|in_review|final|signed),
                    valuer_id, signed_at?, created_at
valuation_approaches id, valuation_id, method(sales|income|cost),
                    indicated_value NUMERIC, weight NUMERIC,
                    rationale, inputs(jsonb)
                    -- weights must sum to 1; enforced in S9
valuation_lines     id, valuation_id, approach_id?, ord, label,
                    amount NUMERIC, basis, source_ref(jsonb)
                    -- source_ref is the provenance chain; S12

leases              id, property_id, unit_id?, tenant, start_date, end_date,
                    lock_in_until?, rent NUMERIC, rent_period,
                    deposit NUMERIC, area NUMERIC, status
lease_escalations   id, lease_id, effective_on, kind(pct|amount), value NUMERIC
rent_roll_lines     id, property_id, as_of, unit_id?, lease_id?,
                    contracted_rent NUMERIC, effective_rent NUMERIC,
                    vacancy_flag, wault_months NUMERIC

construction_stages id, property_id, ord, name, planned_pct NUMERIC,
                    actual_pct NUMERIC, certified_on?, certified_by?
disbursements       id, property_id, stage_id, sanctioned NUMERIC,
                    released NUMERIC, released_on, balance NUMERIC

rera_projects       id, property_id, state, registration_no, registered_on,
                    valid_until, promoter, escrow_account
rera_filings        id, rera_project_id, kind(quarterly|annual|amendment),
                    period, due_on, filed_on?, status, deliverable_id?
approvals           id, property_id, kind(cc|oc|noc_fire|noc_env|layout),
                    authority, ref_no, issued_on, valid_until?, document_id?

deliverables        id, mandate_id, job_id?, doc_type, title,
                    status(draft|in_review|final|signed),
                    reviewed_by?, signed_by?, signed_at?,
                    s3_key, current_version, created_at
deliverable_versions   id, deliverable_id, version, s3_key, created_by, note
deliverable_sections   id, deliverable_id, ord, section_type, content,
                       valuation_line_ids(uuid[]), document_ids(uuid[])
                       -- section → figure AND section → evidence; S12

jobs                id, firm_id, user_id, mandate_id?, status, job_type,
                    instructions, import_ids(uuid[]),
                    idempotency_key(uniq), error, created_at, terminal_at
node_runs           id, job_id, node, attempt, status, latency_ms, error
cost_entries        id, job_id, node, provider, model,
                    tokens_in, tokens_out, inr_cost NUMERIC, created_at
permissions         id, firm_id, subject, subject_id, resource, resource_id,
                    level(read|comment|edit|owner), expires_at
audit_events        id, firm_id, actor_id, action, resource, resource_id,
                    meta(jsonb), ip, created_at
webhook_deliveries  id, job_id, url, attempt, status_code, signature
usage_counters      id, firm_id, period, deliverables, properties, inr_spent
```

Alembic policy: one revision per logical change, **always hand-review the autogenerated migration** — autogenerate does not emit PostGIS GiST indexes on `geom`, and it will happily type a money column as `Float` if a model is careless.

---

## 5. API surface (`/api/v1`)

```
POST /auth/signup   POST /auth/signin   GET /auth/google/callback

GET  /clients       POST /clients
GET  /mandates      POST /mandates      GET /mandates/{id}
GET  /properties    POST /properties    GET /properties/{id}

POST /documents                  # presigned PUT, then OCR + extract
GET  /properties/{id}/documents  GET /properties/{id}/title-chain
GET  /properties/{id}/encumbrances

POST /imports                    # comparables, rent roll, stages, portfolio
POST /imports/{id}/commit
GET  /imports/{id}               # parsed / rejected / duplicate counts
GET  /imports/{id}/rejected      # ★ every dropped row, with a reason

GET  /comparables?property_id=&radius_m=   # map-first, spatial
POST /comparables                POST /comparables/{id}/adjustments
PATCH /comparables/{id}          # verify, reject with reason

POST /valuations                 # basis + premise + approaches
GET  /valuations/{id}            # approaches, weights, lines, range
POST /valuations/{id}/approaches # add or reweight, rationale required
POST /valuations/{id}/sign       # IBBI-registered valuer only

GET  /properties/{id}/rent-roll?as_of=
GET  /properties/{id}/construction
GET  /rera/{project_id}/filings  # obligations, due dates, status

POST /generate                   # + mandate_id, property_id, import_ids
GET  /jobs/{id}                  GET /jobs/{id}/events        # SSE progress
GET  /deliverables   GET /deliverables/{id}
GET  /deliverables/{id}/provenance   # section → figure → comparable → document
POST /deliverables/{id}/review       POST /deliverables/{id}/sign
GET  /deliverables/{id}/export?format=docx|pdf|xlsx|json

GET  /audit          GET /usage
POST /webhooks/test  GET /health
```

Deprecated aliases `POST /generate` and `GET /status/{job_id}` stay mounted through S5, then 410.

---

## 6. Config / env

```
# backend/.env.example
DATABASE_URL=postgresql+asyncpg://...      REDIS_URL=redis://...
GROQ_API_KEY=...       ROUTER_MODEL=llama-3.3-70b-versatile
ANTHROPIC_API_KEY=...  DRAFTER_MODEL=claude-sonnet
S3_BUCKET=...          AWS_REGION=ap-south-1     KMS_KEY_ID=...
PRESIGN_TTL_SECONDS=900     MAX_IMPORT_MB=200
OCR_ENGINE=tesseract        OCR_LANGS=eng+hin
COMPARABLE_RADIUS_M=2000    COMPARABLE_MIN_SAMPLE=3
COMPARABLE_MAX_AGE_MONTHS=18
ROUNDING_POLICY=half_up     MONEY_DP=2      DEFAULT_AREA_UNIT=sqft
JWT_SECRET=...         GOOGLE_CLIENT_ID=...  GOOGLE_CLIENT_SECRET=...
MFA_REQUIRED=true
WEBHOOK_URL=...        WEBHOOK_SIGNING_SECRET=...
CORS_ORIGINS=http://localhost:5173
PORT=8004              SENTRY_DSN=...
DOC_RETENTION_DAYS=2920
```

```
# frontend/.env.example — public by definition; never a secret
VITE_API_BASE_URL=http://localhost:8004/api/v1
VITE_MAP_STYLE_URL=...
VITE_SENTRY_DSN=...
```

`envConfig.py` uses pydantic-settings and **fails at import** on a missing required var, naming it. On the frontend, any `VITE_` variable is compiled into the bundle served to strangers — no secret ever gets that prefix.

---

## 7. The 21 sprints (2-week cadence; file-level + exit proof)

Exit proofs are **running artifacts** — a job id, a valuation traced to adjusted comparables, a rejected row with a reason, a title assertion linked to a registered document, a denied cross-firm request. Not "the test passes."

### Phase 0 — Monorepo, foundation, tenancy (S1–S5)

**S1 · Monorepo split + typed config, zero behaviour change.** Create `backend/` and `frontend/` per §3. Move `api_bridge.py`→`routers/`+`controllers/`, `config.py`→`configs/envConfig.py`+`jobTypes.py` (pydantic-settings), `re_graph.py`→`services/graph/` (still one file, split in S10), `valuation_calculator.py`→`services/valuation/`, `property_data_parser.py`→`services/ingest/`, `re_renderer.py`→`services/render/`. Add `pyproject.toml`+`uv.lock`, `.python-version`, `backend/main.py`, root `Makefile`, `docker-compose.yml` (postgres+postgis, redis), `CLAUDE.md`. Scaffold `frontend/` per §3 with every directory present. *Exit:* before restructuring, save a **golden run** — one valuation report, one RERA quarterly filing, one lease agreement, one rent roll from fixed inputs at `temperature=0.2`, stored in `backend/tests/golden/`. After, identical job type, section sequence and **identical figures to the rupee**; diff committed. `make dev` brings up postgis, redis, the API and Vite with one command. A directory diff of `backend/app` against `ai-chat-be/app` shows the same nine directories, and `frontend/src` against `etl-student-frontend/src` the same set. Boot with `GROQ_API_KEY` unset → exits non-zero naming that variable.

**S2 · Postgres + PostGIS, Alembic, and the death of `jobs.json`.** `models/job.py`, `repositories/jobRepository.py`, `alembic init` + first revision (`firms`, `users`, `jobs`), PostGIS enabled with GiST indexes on `geom` **hand-added**. **Terminal-finality guard**: a write to `status` is rejected at the repository layer when `terminal_at IS NOT NULL`. A schema test forbids `Float` on any monetary column. *Exit:* `alembic upgrade head` clean on an empty DB; `\d properties` shows the GiST index; start a job, `kill -9` mid-graph, restart — the job is visible and reconcilable, not vanished; a deliberate `Float` money column fails CI.

**S3 · Layered HTTP + generated API types.** `routers/{health,generation,jobs}.py` → `controllers/` → `services/` → `repositories/`. `schemas/request/generateRequest.py`, `validators/generateValidator.py` (`job_type` ∈ `ALL_JOB_TYPES`, payload capped, `basis` and `purpose` required for valuation jobs). `packages/api-types` generated from OpenAPI, consumed by `frontend/src/global/apiClient.ts`. *Exit:* `/docs` renders a complete spec; `job_type: "bank_valuation"` returns 422 naming the field and listing valid values; a valuation request without a `basis` is rejected rather than silently defaulting to market value; **a backend schema change without regenerated types fails CI**; every route handler is under 15 lines with no SQL.

**S4 · Real queue: arq + Redis.** `workers/arqApp.py`, `workers/tasks.py:run_generation` and `ocr_document`, `utils/idempotency.py` (key = SHA-256 of normalised instructions + job_type + import checksums + firm_id). Web enqueues, returns 202. `render.yaml` gains a worker service. *Exit:* 20 concurrent jobs all reach a terminal state, none lost; the same import submitted twice inside the window returns one `job_id` and one execution; a worker killed mid-OCR resumes without duplicating pages.

**S5 · Auth, firms, mandates, tenancy.** `models/firm.py`+`user.py`+`client.py`+`mandate.py`, `controllers/authController.py`, JWT + Google OAuth + **enforced MFA**, roles `partner|valuer|analyst|readonly|client`, with `ibbi_reg_no` and asset class recorded on valuer accounts. Scoping at the **repository** layer, never the router. Frontend `features/auth/` + `router/guards.tsx`. *Exit:* firm A cannot read, list, search or download any job, property or deliverable of firm B — all four attempted and denied, returning 404 rather than 403; an `analyst` cannot sign a valuation; a code review confirms no repository method is callable without a firm scope. **Not compressible** — until this ships, multiple clients' title and transaction data sit in one undifferentiated pile.

### Phase 1 — Valuations that hold up (S6–S9)

Nothing in Phase 2 matters if the value is not defensible. This phase is the product.

**S6 · Decimal migration, units, and parser hardening.** Convert every computation in `services/valuation/` to `Decimal` with an explicit rounding policy in `valuation/money.py`; every monetary DB column to `NUMERIC(18,2)`. Build unit conversion (sqft ↔ sqm ↔ acre ↔ guntha ↔ bigha, state-aware) in `utils/geo.py` and `frontend/src/utils/area.ts` from a single shared table. `ingest/detect.py` (explicit, caller-overridable), `parsers/*.py` per source with `schemas/` validation, every input row captured with `parse_status` and `reason`. **An unrecognised format is an error, not an empty structure.** *Exit:* a portfolio of 200 properties totals identically whether summed per property or in aggregate, to the rupee; a bigha-denominated land parcel converts correctly for its state and the conversion is asserted against the notified factor; parsed + rejected + duplicate **sum exactly to row count** for every fixture; a malformed comparable sheet fails loudly naming the row rather than returning an empty set.

**S7 · The comparable adjustment grid — the defect that blocks professional use.** Build `comparable_adjustments` and `valuation/adjust.py`: per-comparable adjustment for size, age, floor, frontage, view, condition, transaction date, location and distress, each with a percentage and a **written rationale**, applied in a defined order to produce an adjusted rate per comparable. **Delete the raw trimmed mean as a value conclusion** — it survives only as a pre-adjustment sanity statistic. `validators/comparableValidator.py` enforces sample adequacy: minimum comparable count, maximum age, maximum radius, and a **blocking error when the adjusted spread exceeds a threshold**, because a wide spread means the comparables are not comparable. Frontend `features/comparables/` with a map and an editable adjustment grid. *Exit:* a valuer takes eight raw comparables, applies adjustments in the console, and the report shows an adjustment grid a reviewer can follow line by line; the same eight comparables produce a materially different (and defensibly better) rate than the old trimmed mean, with both shown in the commit; a valuation attempted with two comparables is **refused** naming the minimum; a valuation whose adjusted rates span more than the configured threshold is blocked with the outliers named; an IBBI-registered valuer reviews one full grid and signs it.

**S8 · The evidence gate.** `validators/evidenceValidator.py`: every assertion of legal or physical fact in a deliverable — ownership, tenure, encumbrance status, approvals held, area, age — must resolve to a `property_document`, a `title_chain_entry`, an `encumbrance` row or an `approval` row. **An unsupported assertion blocks the render**; it is never softened into hedged prose. `graph/nodes/evidenceCheck.py` inserted before the structure nodes. *Exit:* generate a valuation report for a property with no uploaded encumbrance certificate → the job terminates as `blocked_evidence` naming the missing document, and nothing renders; a report asserting "clear and marketable title" with no title chain is blocked; a complete property renders with every factual assertion linked to a document a reviewer can open. This gate has no bypass flag — an unevidenced title assertion in a signed valuation is the claim that ends a valuer's registration.

**S9 · Three approaches and their reconciliation.** `valuation/incomeApproach.py` (NOI, cap rate, DCF) and `costApproach.py` (replacement cost less depreciation) as first-class methods alongside `salesComparison.py`, each producing a `valuation_approach` row with an indicated value; `valuation/reconcile.py` producing a weighted conclusion where **weights must sum to 1 and each weight carries a rationale**. Basis of value (`market|fair|liquidation|distress|insurable`) and premise drive which approaches are mandatory for the mandate's purpose. Frontend `features/valuations/` showing approaches side by side with a value-range bar. *Exit:* a tenanted commercial property is valued by all three approaches and reconciled to a single figure with a written rationale per weight; weights that do not sum to 1 are refused by the API; a mandate whose purpose requires the income approach cannot be concluded on sales comparison alone; a valuer compares the reconciled figure against their own manual working and signs off or lists defects.

### Phase 2 — Deliverables and review workflow (S10–S13)

**S10 · Split `re_graph.py` + golden-set harness.** 686 lines → `graph/state.py`, `routes.py`, `builder.py` (pure wiring), `nodes/*.py` (16+ modules), `prompts/*.py`. Build `tests/golden/` to one fixture per job type with structural assertions per family: valuations need scope, basis, premise, property description, market commentary, approaches, adjustment grid, reconciliation, assumptions and limiting conditions; RERA filings need the state's prescribed schedule; agreements need parties, recitals, consideration, covenants and a schedule of property. *Exit:* the golden set reproduces identical section plans **and identical figures** across all 16 job types; no module in `graph/` exceeds 200 lines; `builder.py` holds zero prompt text; a deliberate prompt change that drops the assumptions and limiting conditions is caught by the harness.

**S11 · Renderer hardening + model routing + cost ledger.** `render/clauseRegistry.py` — an unregistered section type raises rather than falling through to a generic paragraph. **`validators/figureProvenanceValidator.py` enforces the separation that defines this product: no number may appear in rendered output unless it came from a `valuation_line`.** A figure the model wrote in prose is a blocking error. `llm/router.py` maps node→model; `llm/ledger.py` writes a `cost_entries` row per call. *Exit:* an unregistered section type fails explicitly naming it; a model that writes "the property is worth ₹4.2 crore" where no valuation line holds that figure **blocks the render**, demonstrated with a deliberately prompted case; across the golden set zero valuation lines are dropped; **one run's INR figure hand-calculated from provider pricing and matched to the ledger to the paisa**.

**S12 · Provenance, documents, and the audit trail.** Backend: `deliverable_sections.valuation_line_ids` and `document_ids`, `valuation_lines.source_ref`, `GET /deliverables/{id}/provenance`, `audit_events` on every read and export. Frontend: click a figure in a report, see the valuation line, see the adjusted comparables behind it, see the source sheet; click a title statement, see the registered instrument. *Exit:* for a generated valuation report, **every figure traces to adjusted comparables and every factual assertion to a document** a reviewer can open — checked by hand end to end for a full report; a figure or assertion with no chain is blocked; every export appears in the audit log with actor, IP and timestamp.

**S13 · Review notes, sign-off, encryption, retention.** Frontend `features/review/` — raise a note against a section or a comparable, assign, respond, close; analyst prepares, valuer reviews, **partner or registered valuer signs**. Backend: SSE-KMS with per-firm keys on documents and photographs; `redaction.py` so no owner name, survey number or exact coordinate reaches log storage; retention sweeps; **the sign-off gate** — a valuation cannot reach `signed` except by a user with an `ibbi_reg_no` covering that asset class, no deliverable may be signed with an open review note, and unsigned exports carry a "Draft — not for reliance" watermark. *Exit:* an analyst prepares, a valuer raises six notes, the analyst responds, and only then can the valuation be signed; an attempt to sign by a user without a matching registration is refused naming the requirement; an attempt to sign with an open note is refused naming the note; `grep` across a day of production logs finds zero owner names or survey numbers; an unsigned export carries the watermark and a signed one does not.

### Phase 3 — Product depth (S14–S17)

**S14 · RERA, approvals and statutory compliance.** `compliance/rera.py` with state-wise registration and quarterly obligations, `approvals` tracking (CC, OC, fire and environment NOCs, layout) with validity and expiry, `compliance/stampDuty.py` with state rates and the circle-rate floor for transaction documents, and a due-date engine for filings. Frontend `features/rera/` obligation calendar. *Exit:* a project's quarterly RERA obligations are generated for its state with correct due dates checked against the state authority's notified schedule; an approval expiring within 90 days is flagged on the dashboard; a sale deed's stamp duty is computed against both consideration and circle rate with the higher applied, verified by hand for two states; a RERA practitioner reviews one full quarterly filing and signs off or lists defects.

**S15 · Report depth and export breadth.** Strengthen `sectionDrafter.py` and its prompts for valuation reports: scope and purpose, basis and premise, property and locality description, market commentary, methodology per approach, the adjustment grid, reconciliation, assumptions, limiting conditions, valuer's declaration and certificate. Exporters for DOCX, PDF, **XLSX rent roll and adjustment grid with formulas intact**, and JSON. *Exit:* a real valuation report reviewed against an IBBI/RICS-style reporting checklist by a registered valuer who signs it; the XLSX adjustment grid opens in Excel with live formulas rather than flattened values, so a reviewer can change an adjustment and see the rate move; a bank credit officer reads the report and confirms it answers what their credit note requires.

**S16 · Portfolio, rent roll depth, and the client view.** Rent roll with WAULT, expiry profile, vacancy and escalation schedule as of any date; portfolio roll-up across properties with concentration by tenant, city and asset class; construction disbursement tracking against certified stages. Frontend `features/dashboard/` plus a read-only `client` role scoped to a single mandate. *Exit:* a 40-property portfolio produces a rent roll whose total ties to the sum of its lines to the rupee, and a WAULT figure verified by hand against the lease schedule; a client user reads their own mandate and provably nothing else, tested against all four access paths; a disbursement request exceeding the certified stage percentage is flagged rather than paid.

**S17 · Retrieval over the firm's own reporting corpus.** pgvector + hybrid search over the firm's past valuation reports, market commentary and house wording, **scoped per firm and never across clients**, so the section drafter reuses the firm's locality commentary and methodology language rather than generic text. Retrieval feeds commentary only — **never figures or factual assertions**, which continue to come from `valuation_lines` and `property_documents`. *Exit:* a generated market commentary reuses the firm's house wording for a locality it has valued before, shown side by side against the ungrounded version and preferred by a valuer; a crafted request attempting retrieval across a firm boundary returns nothing and raises an audit event; a test confirms no retrieved text carrying a number or a title assertion can reach rendered output without a matching line or document.

### Phase 4 — Production (S18–S21)

**S18 · Integration surface: webhooks, SSE, quotas.** `webhookService.py` (HMAC-SHA256 over the raw body, timestamp in the signed payload, backoff, a `webhook_deliveries` row per attempt) — banks and NBFCs consume valuation completion callbacks directly into their LOS. `node_runs` on every node entry/exit; `GET /jobs/{id}/events` streaming SSE (`parsed 34 comparables`, `reconciling approaches`, `drafting section 4/9`); per-plan deliverable and property quotas with rate limits. *Exit:* a bank's sandbox verifies a signed webhook and rejects a one-character-tampered body; three failing deliveries show increasing backoff then a dead-letter; the console shows a readable progress narrative on a live job; an exhausted quota returns 429 handled as a real UI state, never a 500.

**S19 · Observability, testing, CI/CD.** structlog with `job_id`/`mandate_id` correlation through `redaction.py`, Sentry on both apps, per-node latency from `node_runs`. pytest for parsers, adjustments, approaches, evidence and authz; Vitest + RTL for feature hooks; Playwright for the critical path: login → mandate → property → documents → comparables → adjust → value → generate → review → sign → export. **Path-filtered GitHub Actions**: `backend.yml` (uv sync · ruff · mypy · pytest · `uv export` drift · **pip-audit** · money-column schema test) and `frontend.yml` (yarn lint · tsc -b · vitest · playwright · build). `render.yaml` for api + worker + Postgres/PostGIS + Redis with `alembic upgrade head` as **pre-deploy**; `vercel.json` for the console. *Exit:* a `job_id` alone reconstructs a full lifecycle from logs in one query; a PR touching only `frontend/` does not run the backend suite; a PR adding a dependency without re-exporting `requirements.txt` fails CI; the Playwright critical path passes against a live preview deploy, not a mock.

**S20 · Security, confidentiality, retention.** Rotate every credential. Threat-model the ingestion path — **formula injection in XLSX exports** (a tenant name beginning `=` becomes a formula in Excel) must be neutralised; malicious PDFs in the OCR path must be sandboxed; SSRF review of any URL fetched from imported data. Authorization matrix exercised across every role × resource × action. Frontend XSS review — tenant names, addresses and narrations are client-controlled text rendered in the console. **Location privacy:** exact coordinates and owner names are sensitive; confirm they are redacted from logs and excluded from any client-role response. *Exit:* a tenant name beginning `=cmd` exports as inert text, proven by opening the XLSX; a crafted PDF does not escape the OCR worker, proven by test; the authorization matrix runs programmatically with no gaps; a client-role response contains no exact coordinate or owner name; a written data-flow note covering what is stored, where, for how long, and which third parties see it.

**S21 · Load, cost, closed beta.** k6 or locust driving concurrent generations and bulk ingestion; frontend bundle split per route with a committed visualizer report (the map library is the heavy one — lazy-load it inside `features/comparables/` only); accessibility pass on the adjustment grid. *Exit:* N concurrent generations sustained with p95 documented per job family; a 500-property portfolio import ingests within a stated budget with memory profile recorded; the map stays responsive with 500 comparable markers, measured; **cost per deliverable within budget, hand-verified against the ledger**; a beta cohort of valuation firms and one lender runs real mandates end to end across at least 8 job types, and every defect is filed with its `job_id` and grows the golden set by one fixture per defect class.

---

## 8. Sprint map at a glance

| Phase | Sprints | Backend | Frontend |
|---|---|---|---|
| 0 · Foundation | S1–S5 | monorepo split · PostGIS + Alembic · layered HTTP · arq · **auth + tenancy** | scaffold · generated API types · auth + guards |
| 1 · Valuation | S6–S9 | **Decimal + units** · **adjustment grid** · **evidence gate** · three approaches | map + comparables · adjustment grid · approaches |
| 2 · Deliverables | S10–S13 | graph split + golden set · renderer + figure provenance · provenance chain · encryption | provenance view · review notes · sign-off |
| 3 · Depth | S14–S17 | RERA + approvals + stamp duty · report depth + XLSX · portfolio + rent roll · firm-scoped RAG | obligation calendar · dashboard · client view |
| 4 · Production | S18–S21 | webhooks + SSE + quotas · observability · security + privacy · load | live progress · E2E · bundle + a11y |

---

## 9. CI/CD & deploy

- **Path filtering is the point of the monorepo.** `backend.yml` on `backend/**`, `frontend.yml` on `frontend/**`, both on `packages/api-types/**`.
- **Type generation is a CI gate, not a convention.** A backend schema change not reflected in `packages/api-types` fails the build.
- **The money-column test is blocking.** Any monetary field typed as `Float` in a model or `float8` in a migration fails CI.
- **PostGIS indexes are hand-written.** Autogenerate does not emit GiST on `geom`; the migration review must catch it or spatial comparable search silently degrades to a sequential scan.
- **Migrations run as a Render pre-deploy command.** Never inside the web process. Every revision needs a working, hand-reviewed `downgrade()`.

---

## 10. Cross-cutting discipline

- **The model never produces a number.** Figures come from `valuation_lines` or they do not render. S11 enforces it structurally rather than by prompt instruction.
- **The model never asserts a fact about title.** Ownership, tenure, encumbrance and approvals resolve to a document or the render blocks. S8's gate has no bypass.
- **An unadjusted mean is not a valuation.** Every comparable carries its adjustments and a written rationale; the grid is the report's defensibility.
- **Approaches are reconciled, never averaged blindly.** Weights sum to 1 and each carries a rationale.
- **`Decimal` everywhere, and one unit table.** No `float` touches money, and sqft/sqm/bigha conversion comes from a single shared source used by both apps.
- **Nothing is dropped silently.** Parsed + rejected + duplicate must equal input rows, and the rejected list is visible in the console.
- **Tenancy is enforced at the repository layer**, never the router. This system holds multiple clients' title and transaction data.
- **Location and ownership are sensitive.** Exact coordinates, owner names and survey numbers stay out of logs and out of client-role responses.
- **The output is a draft** until a registered valuer signs it. The watermark is the default.
- **Exit proofs are artifacts.** A valuation traced to adjusted comparables, a title assertion linked to a registered instrument, a rejected row with a reason, a denied cross-firm request, a signed valuer checklist.

---

## 11. Three decisions to confirm before S1

1. **Which regulated basis you are building for.** IBBI-registered valuation for IBC and Companies Act purposes, bank panel valuation for lending, and internal developer feasibility have materially different reporting requirements and sign-off rules. The plan assumes the first two. If the buyer is developers doing feasibility, S8's evidence gate and S13's registration check are overbuilt and S14's RERA work is underbuilt. Decide before S5, because the sign-off model follows from it.
2. **Who maintains the jurisdictional data.** State RERA rules, stamp duty rates, circle rates and unit conventions (bigha alone varies by state and district) are living content. This is a **standing cost with an owner and a review cadence**, not a one-time seeding task. Decide before S14.
3. **`repositories` vs `respositories`.** `ai-chat-be` has the directory misspelled. This plan uses the correct spelling. Match the typo for cross-repo muscle memory, or fix it — the only bad outcome is one of each.
