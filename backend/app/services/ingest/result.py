"""
What a parse returns.

The rule this file exists to enforce: **parsed + rejected + duplicate equals the
input row count, always**. The prototype dropped unrecognised rows on the floor
and returned what was left, so a comparable sheet with eight rows and three
unreadable ones produced a valuation over five comparables that looked like a
valuation over eight. Nobody downstream could tell.

Every rejected row keeps its number, its raw content and a reason. `GET
/imports/{id}/rejected` (S6's API surface) hands that list to the console, and
the valuer decides — rather than the parser deciding silently on their behalf.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ParseStatus(StrEnum):
    PARSED = "parsed"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class ParsedRow:
    row_number: int  # 1-based, counting the header as row 1, as a spreadsheet does
    status: ParseStatus
    data: dict[str, Any] | None = None
    reason: str | None = None
    raw: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status is ParseStatus.PARSED and self.data is None:
            raise ValueError("a parsed row must carry data")
        if self.status is not ParseStatus.PARSED and not self.reason:
            raise ValueError(f"a {self.status.value} row must carry a reason")


@dataclass
class ParseResult:
    source_format: str
    schema_version: str
    rows: list[ParsedRow] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def parsed(self) -> list[dict[str, Any]]:
        return [r.data for r in self.rows if r.status is ParseStatus.PARSED and r.data]

    @property
    def rejected(self) -> list[ParsedRow]:
        return [r for r in self.rows if r.status is ParseStatus.REJECTED]

    @property
    def duplicates(self) -> list[ParsedRow]:
        return [r for r in self.rows if r.status is ParseStatus.DUPLICATE]

    @property
    def input_row_count(self) -> int:
        return len(self.rows)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "input": self.input_row_count,
            "parsed": len(self.parsed),
            "rejected": len(self.rejected),
            "duplicate": len(self.duplicates),
        }

    def assert_reconciles(self) -> None:
        """
        Nothing is dropped silently.

        Called at the end of every parse. If it ever fires, a row went missing
        between reading and reporting, and the counts the console shows are a
        lie — which is exactly the failure this class was written to prevent.
        """
        c = self.counts
        if c["parsed"] + c["rejected"] + c["duplicate"] != c["input"]:
            raise AssertionError(
                f"row counts do not reconcile for {self.source_format}: "
                f"{c['parsed']} parsed + {c['rejected']} rejected + "
                f"{c['duplicate']} duplicate != {c['input']} input rows"
            )

    def summary(self) -> str:
        c = self.counts
        parts = [f"{c['parsed']} parsed"]
        if c["rejected"]:
            parts.append(f"{c['rejected']} rejected")
        if c["duplicate"]:
            parts.append(f"{c['duplicate']} duplicate")
        return f"{self.source_format}: {', '.join(parts)} of {c['input']} rows"

    def to_dict(self) -> dict[str, Any]:
        """
        The shape the graph and the API consume.

        `records` keeps the key the calculator already reads; `counts` and
        `rejected` are what make the drop visible.
        """
        return {
            "format": self.source_format,
            "schema_version": self.schema_version,
            "records": self.parsed,
            "counts": self.counts,
            "rejected": [
                {"row": r.row_number, "reason": r.reason, "raw": r.raw}
                for r in self.rejected + self.duplicates
            ],
            "metadata": self.metadata,
        }


class UnrecognisedFormatError(ValueError):
    """
    The input matches no known format.

    An error, not an empty structure. The prototype returned
    `{"format": "generic_csv", "records": [...]}` for anything it did not
    recognise, and a valuation over zero usable comparables rendered
    successfully.
    """

    def __init__(self, headers: list[str], known: list[str]):
        self.headers = headers
        self.known = known
        super().__init__(
            f"no known format matches these columns: {', '.join(headers) or '(none)'}.\n"
            f"Expected one of: {', '.join(known)}.\n"
            f"Pass an explicit `source_format` to override detection."
        )


class MalformedInputError(ValueError):
    """The input is not parseable at all — not a CSV, not JSON, empty."""
