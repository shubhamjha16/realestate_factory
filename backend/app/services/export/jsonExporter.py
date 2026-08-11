"""
JSON Exporter service (S15).
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

from app.configs.envConfig import settings

OUTPUT_DIR = settings.OUTPUT_DIR


def export_valuation_json(
    clause_plan: Sequence[dict[str, Any]],
    doc_type: str,
    client_name: str,
    property_address: str,
    computed: dict[str, Any] | None = None,
    job_id: str = "job",
) -> str:
    """
    Generate machine-readable JSON report deliverable.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{job_id}_{doc_type}.json")

    payload = {
        "job_id": job_id,
        "doc_type": doc_type,
        "client_name": client_name,
        "property_address": property_address,
        "computed_metrics": computed or {},
        "sections": list(clause_plan or []),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    return out_path
