"""
Property data ingest — the entry point.

    parse_property_data(raw, source_format=None) -> ParseResult

Detection is explicit and caller-overridable. An unrecognised format raises;
so does a payload that is not parseable at all. Neither returns an empty
structure, because the prototype's habit of doing so is what let a valuation
over zero comparables render successfully.

Per-format behaviour lives in `schemas/definitions.py` as data and is applied by
`parsers/rowParser.py`. There is deliberately no per-format parser module doing
its own thing: five hand-written loops drift, and the drift shows up as a field
that is silently dropped for one format and not another.

Land records get one extra step — their areas are converted to square feet
through the state-aware table, because a bigha is not one area.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services.ingest.detect import detect, read_rows
from app.services.ingest.parsers.rowParser import parse_rows
from app.services.ingest.result import ParsedRow, ParseResult, ParseStatus
from app.utils.geo import (
    AmbiguousUnitError,
    UnknownUnitError,
    UnverifiedFactorError,
    to_sqft,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def parse_property_data(
    raw: str,
    *,
    source_format: str | None = None,
    allow_unverified_units: bool = False,
) -> ParseResult:
    headers, rows = read_rows(raw)
    detection = detect(headers, source_format=source_format)

    result = parse_rows(detection.schema, headers, rows)
    result.metadata.update(
        {
            "detected": not detection.explicit,
            "confidence": detection.confidence,
            "matched_columns": list(detection.matched_columns),
        }
    )

    if detection.schema.key == "land_records":
        _convert_land_areas(result, allow_unverified=allow_unverified_units)

    logger.info("%s", result.summary())
    result.assert_reconciles()
    return result


def _convert_land_areas(result: ParseResult, *, allow_unverified: bool) -> None:
    """
    Normalise every parcel to square feet through the shared table.

    A parcel whose unit cannot be resolved for its state is **rejected**, not
    converted on a guess. A bigha taken as the Uttar Pradesh figure when the
    parcel is in West Bengal overstates it by 87%, and the report that carries
    it looks entirely normal.
    """
    converted: list[ParsedRow] = []

    for row in result.rows:
        if row.status is not ParseStatus.PARSED or not row.data:
            converted.append(row)
            continue

        data: dict[str, Any] = dict(row.data)
        try:
            sqft = to_sqft(
                Decimal(str(data["area"])),
                str(data["area_unit"]),
                str(data.get("state") or "") or None,
                allow_unverified=allow_unverified,
            )
        except (AmbiguousUnitError, UnknownUnitError, UnverifiedFactorError) as e:
            converted.append(
                ParsedRow(row.row_number, ParseStatus.REJECTED, reason=str(e), raw=row.raw)
            )
            continue

        data["area_sqft"] = sqft
        data["area_original"] = data["area"]
        data["area_original_unit"] = data["area_unit"]
        converted.append(ParsedRow(row.row_number, ParseStatus.PARSED, data=data, raw=row.raw))

    result.rows = converted
    result.assert_reconciles()
