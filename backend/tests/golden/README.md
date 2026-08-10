# The golden set

S1's contract is that moving 1,509 lines into a package changed nothing about
what the engine produces. This directory is the proof.

## What is held

For each case: an **observation** — the resolved job type, the parse result, the
full `computed` dict, the section sequence, every number that reached the
rendered DOCX, and the SHA-256 of the document's text. Recorded against the
pre-S1 flat modules, asserted against `backend/app`.

Figures are compared with `==`, not approximately. A paisa of drift fails.

| Case | Path | Exercises |
|---|---|---|
| `valuation_report` | valuation | 8 comparables → `analyse_comparables`, structure → critic → 9-section drafter loop |
| `rera_quarterly_report` | compliance | 6 construction stages → `analyse_construction_stages`, structure → critic → drafter |
| `lease_agreement` | agreement | no property data, single-shot drafter |
| `rent_roll_report` | reconciliation | 8 leases → `analyse_rent_roll`, zero-LLM clause plan, 75 rendered figures |

## Why the LLM is a cassette

A live model call is not reproducible, so a golden set built on one proves
nothing. Every call goes through `cassette.py`, keyed on a hash of model,
messages, `max_tokens` and `json_mode`. A prompt change misses the cassette and
raises rather than silently replaying.

The canned responses carry **no figures**. The model is already forbidden from
originating a number, and a cassette that invented one would let a real figure
regression pass unnoticed. Every number in an observation came out of
`services/valuation/`.

## Running

```bash
make golden                # replay, assert against expected/
make golden-record         # re-record against the live provider (needs GROQ_API_KEY)
```

Or directly:

```bash
PYTHONHASHSEED=0 python tests/golden/runner.py --target package --mode replay
PYTHONHASHSEED=0 python tests/golden/runner.py --target package --mode record --write-expected
```

`--mode synthesise` fills a cassette miss from the canned responses in
`cassette.py`. That is how these cassettes were authored without provider keys.

## Two things this surfaced

**`PYTHONHASHSEED` has to be pinned.** `intake_node` builds its prompt with
`', '.join(ALL_JOB_TYPES)` over a set, so the prompt text differs between
processes. That is a live defect — it also means the prompt cache never hits —
and it is left in place under S1's zero-behaviour-change rule. S10 fixes it when
prompts become data; `ALL_JOB_TYPES_SORTED` already exists for everything
user-facing.

**A valuation report renders three numbers.** The eight comparables reduce to a
`suggested_rate`, the renderer accepts `computed` — and ignores it. Every figure
in a valuation report today is whatever the model wrote in prose. This is exactly
the separation S11's `figureProvenanceValidator.py` exists to enforce, and the
observations pin the current behaviour so the fix is visible when it lands.
