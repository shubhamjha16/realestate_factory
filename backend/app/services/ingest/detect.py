"""
Format detection — explicit, and always overridable.

Detection is a convenience for a valuer pasting a sheet, never an authority. Any
caller may name the format, and when they do this module is not consulted at all.

When it is consulted and nothing matches, it **raises**. The prototype fell
through to `generic_csv` and handed the calculator a list of dictionaries with
no recognised fields, which produced a valuation over zero comparables that
rendered successfully. An unrecognised format is an error.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass

from app.services.ingest.result import MalformedInputError, UnrecognisedFormatError
from app.services.ingest.schemas.definitions import ALL_SCHEMAS, SCHEMAS_BY_KEY, SourceSchema

_PUNCTUATION = re.compile(r"[^a-z0-9%]+")


def normalise_header(header: str) -> str:
    """`Sale Price (₹)`, `sale-price` and `SALE_PRICE` are all `sale_price`."""
    lowered = (header or "").strip().lower()
    lowered = re.sub(r"\([^)]*\)", " ", lowered)  # drop parenthetical units
    return _PUNCTUATION.sub("_", lowered).strip("_")


@dataclass(frozen=True)
class Detection:
    schema: SourceSchema
    matched_columns: tuple[str, ...]
    confidence: float
    explicit: bool


def read_rows(raw: str) -> tuple[list[str], list[dict[str, str]]]:
    """
    Parse the payload into headers and rows.

    Accepts CSV and a JSON array of objects. Anything else raises, rather than
    producing an empty structure that looks like a successful parse of nothing.
    """
    text = (raw or "").strip()
    if not text:
        raise MalformedInputError("the input is empty")

    if text.startswith(("[", "{")):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise MalformedInputError(f"looks like JSON but is not valid: {e}") from e
        records = data if isinstance(data, list) else [data]
        if not records:
            raise MalformedInputError("the JSON payload contains no records")
        if not all(isinstance(r, dict) for r in records):
            raise MalformedInputError("expected a JSON array of objects")
        headers = list(records[0].keys())
        return headers, [{str(k): str(v) for k, v in r.items()} for r in records]

    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel  # a single-column file sniffs badly; comma is right

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if reader.fieldnames is None:
        raise MalformedInputError("the input has no header row")

    rows = [{(k or ""): (v or "") for k, v in row.items()} for row in reader]
    if not rows:
        raise MalformedInputError(
            f"the input has a header ({', '.join(reader.fieldnames)}) but no data rows"
        )
    return list(reader.fieldnames), rows


def detect(headers: list[str], *, source_format: str | None = None) -> Detection:
    """
    `source_format` wins outright. Otherwise, score each schema.

    Scoring counts signature columns first — they are what makes a format
    recognisable — and falls back to how much of the schema the sheet covers, so
    a comparable sheet and a portfolio sheet that share `area` do not tie.
    """
    if source_format:
        schema = SCHEMAS_BY_KEY.get(source_format)
        if schema is None:
            raise UnrecognisedFormatError(headers, sorted(SCHEMAS_BY_KEY))
        return Detection(schema, tuple(headers), confidence=1.0, explicit=True)

    normalised = {normalise_header(h) for h in headers if h}

    scored: list[tuple[float, Detection]] = []
    for schema in ALL_SCHEMAS:
        signature_hits = {s for s in schema.signature if s in normalised}
        if not signature_hits:
            continue

        known = {alias for f in schema.fields for alias in f.aliases}
        coverage_hits = normalised & known
        # Signature matches dominate; column coverage only breaks ties between
        # formats that share one — a comparable sheet and a portfolio sheet both
        # have `area`, but only one has `sale_price`.
        score = len(signature_hits) + len(coverage_hits) / 100
        confidence = min(1.0, len(coverage_hits) / max(len(schema.required_fields), 1))
        scored.append(
            (score, Detection(schema, tuple(sorted(coverage_hits)), confidence, explicit=False))
        )

    if not scored:
        raise UnrecognisedFormatError(
            sorted(normalise_header(h) for h in headers if h), sorted(SCHEMAS_BY_KEY)
        )
    return max(scored, key=lambda pair: pair[0])[1]
