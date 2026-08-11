#!/usr/bin/env python
"""
Fail if any monetary column is a float.

Property values run to crores. `round(area * rate, 2)` on binary floats produces
figures that will not reconcile across a portfolio, and a rent roll that should
tie will not. Every monetary column in this schema is `NUMERIC(18,2)`.

Two passes, because a column can be wrong in two places:

  models      — every column registered on `Base.metadata`, checked by type.
  migrations  — the revision files, checked by text, because a migration can
                introduce a column the models never declared (a raw `op.execute`,
                or a column added and later removed from the model).

Run by `make lint`, by CI, and by `tests/test_schema_money.py`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sqlalchemy import Float, Numeric
from sqlalchemy.sql.schema import MetaData

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = BACKEND_ROOT / "alembic" / "versions"

MONEY_PRECISION = 18
MONEY_SCALE = 2

# Column-name fragments that denote an amount of money. Deliberately broad: a
# false positive costs one rename or one entry in ALLOWED_NON_MONEY; a false
# negative costs a portfolio that does not add up.
MONEY_NAME_PARTS = (
    "price", "amount", "value", "rent", "deposit", "cost", "consideration",
    "inr", "sanctioned", "released", "balance", "spent", "fee", "duty",
    "premium", "noi", "gdv", "salary", "payable", "receivable", "arrears",
    "overdue", "outstanding",
)

# Names that match the fragments above but are not money.
ALLOWED_NON_MONEY = frozenset({
    "rent_period",       # a unit of time
    "valuer_id",         # a user, not an amount — "valuer" contains "value"
    "valuer_asset_class",
    "value_range_unit",
    "rate_unit",
    "amount_unit",
    "currency",
})

FLOAT_IN_MIGRATION = re.compile(
    r"""sa\.Column\(\s*["'](?P<name>[a-z_]+)["']\s*,\s*
        (?P<type>sa\.Float|sa\.REAL|sa\.Double|postgresql\.DOUBLE_PRECISION|
                 sa\.dialects\.postgresql\.DOUBLE_PRECISION)""",
    re.VERBOSE,
)


def is_money_name(name: str) -> bool:
    if name in ALLOWED_NON_MONEY:
        return False
    return any(part in name for part in MONEY_NAME_PARTS)


def check_metadata(metadata: MetaData) -> list[str]:
    problems: list[str] = []
    for table in metadata.sorted_tables:
        for column in table.columns:
            if not is_money_name(column.name):
                continue
            where = f"{table.name}.{column.name}"
            if isinstance(column.type, Float):
                problems.append(f"{where} is {column.type!r} — money must be NUMERIC(18,2)")
            elif not isinstance(column.type, Numeric):
                problems.append(f"{where} is {column.type!r} — money must be NUMERIC(18,2)")
            elif (column.type.precision, column.type.scale) != (MONEY_PRECISION, MONEY_SCALE):
                problems.append(
                    f"{where} is NUMERIC({column.type.precision},{column.type.scale}) "
                    f"— money must be NUMERIC({MONEY_PRECISION},{MONEY_SCALE})"
                )
    return problems


def check_migrations(versions_dir: Path = VERSIONS_DIR) -> list[str]:
    problems: list[str] = []
    for path in sorted(versions_dir.glob("*.py")):
        source = path.read_text()
        for match in FLOAT_IN_MIGRATION.finditer(source):
            name = match.group("name")
            if is_money_name(name):
                line = source[: match.start()].count("\n") + 1
                problems.append(
                    f"{path.name}:{line} column {name!r} is {match.group('type')} "
                    f"— money must be NUMERIC(18,2)"
                )
    return problems


def main() -> int:
    sys.path.insert(0, str(BACKEND_ROOT))
    import app.models  # noqa: F401  — registers every model on the metadata
    from app.models.base import Base

    problems = check_metadata(Base.metadata) + check_migrations()
    if problems:
        for p in problems:
            print(f"::error::{p}", file=sys.stderr)
        print(f"\n{len(problems)} monetary column(s) typed as float.", file=sys.stderr)
        return 1

    money_columns = sum(
        1
        for t in Base.metadata.sorted_tables
        for c in t.columns
        if is_money_name(c.name)
    )
    print(f"money-column check passed ({money_columns} monetary column(s), all NUMERIC(18,2))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
