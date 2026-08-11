"""
Reporting Corpus Retrieval router (S17).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.routers.deps import current_scope
from app.services.access.scope import FirmScope
from app.services.retrieval import corpus

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class SearchCorpusRequest(BaseModel):
    target_firm_id: UUID
    locality: str = Field(default="")
    topic: str = Field(default="market_analysis")


@router.post("/search", response_model=dict[str, Any])
async def search_corpus_endpoint(
    req: SearchCorpusRequest,
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
):
    return await corpus.search_firm_corpus(
        db=db,
        scope=scope,
        target_firm_id=req.target_firm_id,
        locality=req.locality,
        topic=req.topic,
    )
