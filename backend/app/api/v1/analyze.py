"""Analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import repo_dependency
from app.core.chains import UnsupportedChainError, get_chain
from app.core.config import get_settings
from app.db.repositories import AnalysisRepository
from app.schemas.analysis import (
    AnalysisCreated,
    AnalysisResult,
    AnalysisStatus,
    AnalysisSummary,
    AnalyzeRequest,
)
from app.services.task_queue import submit_analysis

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisCreated, status_code=202)
def start_analysis(
    payload: AnalyzeRequest,
    request: Request,
    repo: AnalysisRepository = Depends(repo_dependency),
) -> AnalysisCreated:
    try:
        get_chain(payload.chain_id)
    except UnsupportedChainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    analysis_id = submit_analysis(payload.chain_id, payload.token_address, payload.analysis_depth)
    return AnalysisCreated(
        analysis_id=analysis_id,
        status=AnalysisStatus.QUEUED,
        poll_url=f"{get_settings().api_prefix}/analyze/{analysis_id}",
    )


@router.get("/analyze/{analysis_id}", response_model=AnalysisResult)
def get_analysis(
    analysis_id: str,
    repo: AnalysisRepository = Depends(repo_dependency),
) -> AnalysisResult:
    row = repo.get(analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result = repo.get_result(analysis_id)
    if result is not None:
        result.status = AnalysisStatus(row.status)
        return result

    # Still queued/running or failed without a stored result.
    return AnalysisResult(
        analysis_id=analysis_id,
        chain_id=row.chain_id,
        token_address=row.token_address,
        status=AnalysisStatus(row.status),
        analysis_depth=row.analysis_depth,
        error=row.error,
    )


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(
    limit: int = 20,
    repo: AnalysisRepository = Depends(repo_dependency),
) -> list[AnalysisSummary]:
    rows = repo.list_recent(limit=min(limit, 100))
    return [
        AnalysisSummary(
            analysis_id=r.analysis_id,
            chain_id=r.chain_id,
            token_address=r.token_address,
            status=AnalysisStatus(r.status),
            risk_score=r.risk_score,
            risk_classification=r.risk_classification,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/stats")
def stats(repo: AnalysisRepository = Depends(repo_dependency)) -> dict:
    return repo.stats()
