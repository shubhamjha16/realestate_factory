# frontend — working notes

Vite + React 19 + TypeScript, yarn, Vercel. Mirrors `etl-student-frontend`
directory for directory. Read the root `CLAUDE.md` first.

## Commands

```bash
yarn dev         # :5173
yarn build       # tsc -b && vite build
yarn lint
yarn typecheck
yarn test        # vitest
```

## Structure

```
src/
  components/    shared, presentational only
    ui/          Button Input Modal Toast Skeleton DataGrid Tabs
    feedback/    ErrorBoundary EmptyState ErrorState
    property/    MapView ComparableCard AdjustmentGrid ValueRangeBar RentRollTable
  features/      one directory per feature, each with an index.ts barrel
  global/        apiClient · errors · env
  hooks/  layouts/  router/  shared/constants/  store/  utils/
```

Two deliberate departures from the mirrored repo:

- **`components/property/`** — the map, comparable cards, the adjustment grid and
  the value-range bar are rendered by five features. Comparables are a map
  problem before a table problem, so the map belongs in shared components rather
  than inside one feature.
- **`utils/area.ts`** alongside `money.ts` — the etl frontend never converts
  units. Here a wrong sqft/sqm/bigha conversion silently multiplies a valuation,
  so unit handling is a first-class utility with its own tests.

## The boundary rule

A feature imports freely from `components/`, `global/`, `hooks/`, `shared/`,
`store/` and `utils/`. It imports another feature **only through that feature's
`index.ts`**. Lint-enforced in `eslint.config.js` — turned on now, while there is
nothing to fix, because unpicking it later is far more expensive.

## Money and area

`utils/money.ts` — money arrives as a **decimal string** and stays one. The
console formats it and never computes with it. `toFixed` on money is a bug:
`(10650000 / 1e7).toFixed(2)` is `"1.06"`, and the correct answer is `1.07`.
`formatLakhCrore` rounds on the digits for exactly this reason.

`utils/area.ts` — factors come from the same shared table the engine uses. Units
whose factor varies by state and district (bigha, biswa, katha, vigha) throw
`AmbiguousUnitError` rather than guessing.

## Environment

Anything with a `VITE_` prefix is compiled into the bundle served to strangers.
No secret ever gets that prefix. `global/env.ts` fails loudly on a missing
required variable, mirroring the backend's posture.

## What is real and what is scaffolding

S1 landed the structure. Real today: `global/`, `hooks/`, `store/`, `utils/`,
`shared/constants/`, `components/ui/`, `components/feedback/`, and the props
contracts in `components/property/`. Every `features/*` barrel is empty and names
the sprint that fills it.
