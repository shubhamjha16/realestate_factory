# Real Estate Factory — console

The console a valuer works in: add a property, upload comparables, adjust them,
review the valuation, sign off, export.

## Getting started

```bash
cp .env.example .env      # VITE_API_BASE_URL must point at a running engine
yarn install
yarn dev                  # http://localhost:5173
```

From the repository root, `make dev` brings up the engine and this console
together, along with Postgres/PostGIS and Redis.

## Scripts

| Command | Does |
|---|---|
| `yarn dev` | Vite dev server on :5173 |
| `yarn build` | `tsc -b` then `vite build` into `dist/` |
| `yarn lint` | ESLint, including the feature boundary rule |
| `yarn typecheck` | `tsc -b --noEmit` |
| `yarn test` | Vitest |

## Deployment

Vercel, configured in `vercel.json`. Set `VITE_API_BASE_URL` in the project's
environment — it is compiled into the bundle, so it is public by definition.

See `CLAUDE.md` for conventions and the rules that are not negotiable.
