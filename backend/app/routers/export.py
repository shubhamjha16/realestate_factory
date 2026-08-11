"""
Multi-format Export router (S15).

Provides endpoints for exporting deliverables in DOCX, PDF, XLSX (live formulas), and JSON formats.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.routers.deps import current_scope
from app.services.access.scope import FirmScope
from app.services.export import docxExporter, jsonExporter, pdfExporter, xlsxExporter

router = APIRouter(prefix="/export", tags=["export"])


class ExportDocxRequest(BaseModel):
    clause_plan: list[dict[str, Any]]
    doc_type: str = Field(default="valuation_report")
    client_name: str = Field(default="Client")
    property_address: str = Field(default="")
    computed: dict[str, Any] = Field(default_factory=dict)
    job_id: str = Field(default="job")
    status: str = Field(default="draft")


class ExportPdfRequest(BaseModel):
    clause_plan: list[dict[str, Any]]
    doc_type: str = Field(default="valuation_report")
    client_name: str = Field(default="Client")
    property_address: str = Field(default="")
    job_id: str = Field(default="job")


class ExportJsonRequest(BaseModel):
    clause_plan: list[dict[str, Any]]
    doc_type: str = Field(default="valuation_report")
    client_name: str = Field(default="Client")
    property_address: str = Field(default="")
    computed: dict[str, Any] = Field(default_factory=dict)
    job_id: str = Field(default="job")


class ExportXlsxGridRequest(BaseModel):
    comparables: list[dict[str, Any]]
    subject_area: Decimal = Field(default=Decimal("1200"))
    export_type: str = Field(default="adjustment_grid")  # "adjustment_grid" or "rent_roll"
    job_id: str = Field(default="job")


@router.post("/docx", response_model=dict[str, Any])
async def export_docx(
    req: ExportDocxRequest,
    scope: FirmScope = Depends(current_scope),
):
    path = docxExporter.export_valuation_docx(
        clause_plan=req.clause_plan,
        doc_type=req.doc_type,
        client_name=req.client_name,
        property_address=req.property_address,
        computed=req.computed,
        job_id=req.job_id,
        status=req.status,
    )
    return FileResponse(path, filename=os.path.basename(path), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.post("/pdf", response_model=dict[str, Any])
async def export_pdf(
    req: ExportPdfRequest,
    scope: FirmScope = Depends(current_scope),
):
    path = pdfExporter.export_valuation_pdf(
        clause_plan=req.clause_plan,
        doc_type=req.doc_type,
        client_name=req.client_name,
        property_address=req.property_address,
        job_id=req.job_id,
    )
    return FileResponse(path, filename=os.path.basename(path), media_type="application/pdf")


@router.post("/json", response_model=dict[str, Any])
async def export_json(
    req: ExportJsonRequest,
    scope: FirmScope = Depends(current_scope),
):
    path = jsonExporter.export_valuation_json(
        clause_plan=req.clause_plan,
        doc_type=req.doc_type,
        client_name=req.client_name,
        property_address=req.property_address,
        computed=req.computed,
        job_id=req.job_id,
    )
    return FileResponse(path, filename=os.path.basename(path), media_type="application/json")


@router.post("/xlsx", response_model=dict[str, Any])
async def export_xlsx(
    req: ExportXlsxGridRequest,
    scope: FirmScope = Depends(current_scope),
):
    out_dir = os.path.join("outputs", "exports")
    os.makedirs(out_dir, exist_ok=True)
    
    if req.export_type == "rent_roll":
        out_path = os.path.join(out_dir, f"{req.job_id}_rent_roll.xlsx")
        path = xlsxExporter.export_rent_roll_xlsx(units=req.comparables, output_path=out_path)
    else:
        out_path = os.path.join(out_dir, f"{req.job_id}_adjustment_grid.xlsx")
        path = xlsxExporter.export_adjustment_grid_xlsx(
            comparables=req.comparables,
            subject_area=req.subject_area,
            output_path=out_path,
        )

    return FileResponse(path, filename=os.path.basename(path), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
