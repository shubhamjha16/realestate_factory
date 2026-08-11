"""
Portfolio Roll-Up & Concentration service (S16).

Aggregates multi-property portfolios with concentration metrics by tenant, city,
and asset class.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def compute_portfolio_rollup(
    properties: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """
    Aggregate portfolio values and compute concentration metrics.
    """
    total_properties = len(properties)
    total_asset_value = Decimal("0.00")
    total_built_up_area = Decimal("0.00")

    city_values: dict[str, Decimal] = defaultdict(Decimal)
    asset_class_values: dict[str, Decimal] = defaultdict(Decimal)
    tenant_values: dict[str, Decimal] = defaultdict(Decimal)

    for p in properties:
        val = Decimal(str(p.get("concluded_value", p.get("asset_value", 0)))).quantize(Decimal("0.01"))
        area = Decimal(str(p.get("built_up_area", p.get("area", 0)))).quantize(Decimal("0.01"))
        city = (p.get("city") or "Unknown").title()
        asset_class = (p.get("property_type") or "Commercial").title()
        tenant = (p.get("top_tenant") or "Multi-tenant").title()

        total_asset_value += val
        total_built_up_area += area

        city_values[city] += val
        asset_class_values[asset_class] += val
        tenant_values[tenant] += val

    def _calc_concentration(val_dict: dict[str, Decimal]) -> list[dict[str, Any]]:
        result = []
        if total_asset_value > Decimal("0.00"):
            for key, val in val_dict.items():
                pct = ((val / total_asset_value) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                result.append({
                    "name": key,
                    "value": str(val),
                    "share_percentage": str(pct),
                })
        result.sort(key=lambda x: Decimal(x["value"]), reverse=True)
        return result

    return {
        "total_properties": total_properties,
        "total_asset_value": str(total_asset_value),
        "total_built_up_area_sqft": str(total_built_up_area),
        "concentration_by_city": _calc_concentration(city_values),
        "concentration_by_asset_class": _calc_concentration(asset_class_values),
        "concentration_by_tenant": _calc_concentration(tenant_values),
    }
