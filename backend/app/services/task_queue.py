"""Background task execution.

Long-running analyses run off the request thread. A thread pool is used by
default so the app is usable without a broker; when ``use_celery`` is enabled a
Celery task is dispatched instead (see celery_app.py).
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories import AnalysisRepository
from app.db.session import SessionLocal
from app.reports.models import SecurityReport
from app.reports.writer import write_reports
from app.services.analysis_service import AnalysisOrchestrator, AnalysisRequest, OrchestrationOutcome

logger = get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analysis")


def run_analysis_sync(analysis_id: str, chain_id: int, token_address: str, depth: str) -> None:
    """Execute an analysis and persist its result + reports."""
    session = SessionLocal()
    repo = AnalysisRepository(session)
    try:
        repo.mark_running(analysis_id)
        outcome: OrchestrationOutcome = AnalysisOrchestrator(
            AnalysisRequest(chain_id=chain_id, token_address=token_address, analysis_depth=depth)  # type: ignore[arg-type]
        ).run()
        result = outcome.result
        result.analysis_id = analysis_id
        repo.save_result(result)

        report = SecurityReport(report_id=analysis_id, result=result)
        paths = write_reports(report)
        repo.attach_report(analysis_id, report.report_id, paths)
        logger.info("Analysis %s completed with score %s", analysis_id, result.risk.score if result.risk else None)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analysis %s failed", analysis_id)
        repo.mark_failed(analysis_id, str(exc))
    finally:
        session.close()


def submit_analysis(chain_id: int, token_address: str, depth: str = "standard") -> str:
    """Create a queued analysis and schedule it. Returns the analysis id."""
    analysis_id = uuid.uuid4().hex
    session = SessionLocal()
    try:
        AnalysisRepository(session).create_queued(analysis_id, chain_id, token_address, depth)
    finally:
        session.close()

    settings = get_settings()
    if settings.use_celery:
        from app.services.celery_app import run_analysis_task

        run_analysis_task.delay(analysis_id, chain_id, token_address, depth)
    else:
        _executor.submit(run_analysis_sync, analysis_id, chain_id, token_address, depth)
    return analysis_id
