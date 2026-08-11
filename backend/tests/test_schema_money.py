"""
No float money. Ever.

This is the check the sprint plan calls blocking, and it is worth being precise
about why: `round(area * rate, 2)` on binary floats gives figures that do not
reconcile. A portfolio summed per property and summed in aggregate disagree by
paise, then by rupees, and a rent roll that must tie to its lines does not. By
the time anyone notices, it is in a signed report.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import Column, Float, MetaData, Numeric, Table

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_money_columns import (  # noqa: E402
    check_metadata,
    check_migrations,
    is_money_name,
)


def _metadata():
    import app.models  # noqa: F401  — registers every model
    from app.models.base import Base

    return Base.metadata


def test_no_monetary_column_in_the_models_is_a_float():
    assert check_metadata(_metadata()) == []


def test_no_migration_introduces_a_float_money_column():
    assert check_migrations() == []


def test_a_deliberate_float_money_column_is_caught():
    """
    The exit proof. A guard nobody has watched fail is not a guard.
    """
    bad = MetaData()
    Table("deals", bad, Column("sale_price", Float))
    problems = check_metadata(bad)
    assert len(problems) == 1
    assert "deals.sale_price" in problems[0]
    assert "NUMERIC(18,2)" in problems[0]


def test_numeric_with_the_wrong_scale_is_also_caught():
    """NUMERIC(10,4) is not money either — it silently changes what rounds where."""
    bad = MetaData()
    Table("deals", bad, Column("consideration", Numeric(10, 4)))
    problems = check_metadata(bad)
    assert len(problems) == 1
    assert "NUMERIC(10,4)" in problems[0]


def test_the_name_heuristic_covers_the_obvious_cases():
    for name in ("sale_price", "monthly_rent", "security_deposit", "inr_cost",
                 "concluded_value", "sanctioned", "released", "stamp_duty"):
        assert is_money_name(name), name
    # ...and does not fire on things that merely read like money
    for name in ("rent_period", "currency", "valuer_asset_class", "valuer_id", "area_unit"):
        assert not is_money_name(name), name


def test_areas_are_exact_too():
    """
    Not money, but the same failure: a rounded area multiplied by a rate is a
    wrong value conclusion.
    """
    properties = _metadata().tables["properties"]
    for name in ("land_area", "built_up_area", "carpet_area"):
        column = properties.columns[name]
        assert isinstance(column.type, Numeric)
        assert not isinstance(column.type, Float)
