"""
DOCX Exporter service facade (S15).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.services.render.docxRenderer import render


def export_valuation_docx(
    clause_plan: Sequence[dict[str, Any]],
    doc_type: str,
    client_name: str,
    property_address: str,
    computed: dict[str, Any] | None = None,
    job_id: str = "job",
    status: str = "draft",
) -> str:
    """
    Generate DOCX report deliverable file.
    """
    return render(
        clause_plan=list(clause_plan or []),
        doc_type=doc_type,
        client_name=client_name,
        property_address=property_address,
        computed=computed or {},
        job_id=job_id,
        status=status,
    )
