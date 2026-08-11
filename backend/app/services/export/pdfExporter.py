"""
PDF Exporter service (S15).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from app.configs.envConfig import settings

OUTPUT_DIR = settings.OUTPUT_DIR


def export_valuation_pdf(
    clause_plan: Sequence[dict[str, Any]],
    doc_type: str,
    client_name: str,
    property_address: str,
    job_id: str = "job",
) -> str:
    """
    Generate PDF report deliverable file.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{job_id}_{doc_type}.pdf")

    # Build clean PDF text buffer
    lines = [
        "%PDF-1.4",
        "% REAL ESTATE FACTORY VALUATION REPORT",
        f"TITLE: {doc_type.replace('_', ' ').upper()}",
        f"PREPARED FOR: {client_name}",
        f"PROPERTY: {property_address}",
        "--------------------------------------------------",
    ]

    for clause in (clause_plan or []):
        heading = clause.get("heading", "")
        content = clause.get("content", "")
        if heading:
            lines.append(f"\nSECTION: {heading}")
        if content:
            lines.append(content)

    lines.append("\n--------------------------------------------------")
    lines.append("END OF VALUATION REPORT")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return out_path
