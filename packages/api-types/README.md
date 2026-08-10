# `@realestate-factory/api-types`

Generated. Do not edit by hand.

TypeScript types produced from the backend's OpenAPI spec and consumed by
`frontend/src/global/apiClient.ts`. Generation and the CI gate land in **S3**: a
backend schema change that is not reflected here fails the build, so a console
that disagrees with the engine cannot ship.

This is the reason the two apps share a repository. Adjustment factors, property
types, unit conventions and rounding policy must match exactly — a console that
converts square metres differently from the engine produces a report whose area
and rate contradict its total.

Until S3, the mirrors are maintained by hand and guarded by tests:

| Backend | Console | Guard |
|---|---|---|
| `app/configs/jobTypes.py` | `src/shared/constants/jobTypes.ts` | `frontend/tests/constants.test.ts` |
| `app/configs/jurisdictionConfig.py` | `src/shared/constants/states.ts` | — |
| `app/utils/geo.py` (S6) | `src/utils/area.ts` | `frontend/tests/utils.test.ts` |
