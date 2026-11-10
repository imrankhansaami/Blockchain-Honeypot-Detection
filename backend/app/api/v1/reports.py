"""Report retrieval and download endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import repo_dependency
from app.db.repositories import AnalysisRepository
from app.reports import html_report, json_report, pdf_report
from app.reports.models import SecurityReport

router = APIRouter(tags=["reports"])

_MEDIA = {
    "json": "application/json",
    "html": "text/html",
    "pdf": "application/pdf",
}


def _report(repo: AnalysisRepository, analysis_id: str) -> SecurityReport:
    result = repo.get_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Report not found or analysis incomplete")
    return SecurityReport(report_id=analysis_id, result=result)


@router.get("/reports/{analysis_id}")
def get_report(
    analysis_id: str,
    repo: AnalysisRepository = Depends(repo_dependency),
) -> dict:
    return json_report.to_dict(_report(repo, analysis_id))


@router.get("/reports/{analysis_id}/download")
def download_report(
    analysis_id: str,
    fmt: str = Query(default="json", alias="format", pattern="^(json|html|pdf)$"),
    repo: AnalysisRepository = Depends(repo_dependency),
) -> Response:
    report = _report(repo, analysis_id)
    if fmt == "json":
        body = json_report.generate(report).encode("utf-8")
    elif fmt == "html":
        body = html_report.render(report).encode("utf-8")
    else:
        body = pdf_report.build(report)

    filename = f"honeypot-report-{analysis_id}.{fmt}"
    return Response(
        content=body,
        media_type=_MEDIA[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
