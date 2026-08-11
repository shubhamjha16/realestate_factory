"""
The row parser, shared by every format.

One implementation driven by the schema definitions, rather than five
hand-written loops that drift apart. Each row comes out `parsed`, `rejected` or
`duplicate`, and a rejected row names the field and says what was wrong with it —
"row 4: sale_price is not a number: 'on request'" rather than a row that vanished.
"""

from __future__ import annotations

from typing import Any

from app.services.ingest.detect import normalise_header
from app.services.ingest.result import ParsedRow, ParseResult, ParseStatus
from app.services.ingest.schemas.definitions import SourceSchema
from app.services.ingest.schemas.fields import Field, FieldError

# Row 1 is the header, as a spreadsheet counts it, so the first data row is 2.
FIRST_DATA_ROW = 2


def _column_index(headers: list[str]) -> dict[str, str]:
    """Normalised header -> the original column name."""
    return {normalise_header(h): h for h in headers if h}


def _pick(row: dict[str, str], index: dict[str, str], field: Field) -> tuple[Any, bool]:
    """Return (raw value, whether the column was present at all)."""
    for alias in field.aliases:
        original = index.get(alias)
        if original is not None:
            return row.get(original, ""), True
    return None, False


def parse_rows(
    schema: SourceSchema,
    headers: list[str],
    rows: list[dict[str, str]],
) -> ParseResult:
    index = _column_index(headers)
    result = ParseResult(source_format=schema.key, schema_version=schema.version)
    seen: dict[tuple, int] = {}

    for offset, raw_row in enumerate(rows):
        row_number = FIRST_DATA_ROW + offset

        # A row of nothing is a trailing blank line, not an error worth a reason
        # that says nothing. It is still counted, so the totals reconcile.
        if not any(str(v).strip() for v in raw_row.values()):
            result.rows.append(
                ParsedRow(row_number, ParseStatus.REJECTED, reason="the row is empty", raw=raw_row)
            )
            continue

        record: dict[str, Any] = {}
        problems: list[str] = []

        for field in schema.fields:
            value, present = _pick(raw_row, index, field)
            blank = value is None or not str(value).strip()

            if blank:
                if field.required:
                    problems.append(
                        f"{field.name} is required but "
                        + ("empty" if present else f"the column is missing "
                           f"(accepted: {', '.join(field.aliases)})")
                    )
                else:
                    record[field.name] = field.default
                continue

            try:
                record[field.name] = field.coerce(value) if field.coerce else value
            except FieldError as e:
                problems.append(f"{field.name} {e}")

        if problems:
            result.rows.append(
                ParsedRow(
                    row_number,
                    ParseStatus.REJECTED,
                    reason="; ".join(problems),
                    raw=raw_row,
                )
            )
            continue

        key = tuple(str(record.get(f, "")).strip().lower() for f in schema.identity)
        if any(part for part in key) and key in seen:
            result.rows.append(
                ParsedRow(
                    row_number,
                    ParseStatus.DUPLICATE,
                    reason=(
                        f"duplicates row {seen[key]} on "
                        f"{', '.join(schema.identity)} — a repeated comparable would "
                        f"weight the same evidence twice"
                    ),
                    raw=raw_row,
                )
            )
            continue

        seen[key] = row_number
        record["_row"] = row_number
        result.rows.append(ParsedRow(row_number, ParseStatus.PARSED, data=record, raw=raw_row))

    result.metadata["columns"] = sorted(index)
    result.assert_reconciles()
    return result
