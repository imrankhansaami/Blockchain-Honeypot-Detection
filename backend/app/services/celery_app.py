"""Optional Celery application for distributed background analysis."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "honeypot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_track_started = True
celery_app.conf.task_time_limit = 600
celery_app.conf.task_soft_time_limit = 540


@celery_app.task(name="analysis.run")
def run_analysis_task(analysis_id: str, chain_id: int, token_address: str, depth: str) -> str:
    from app.services.task_queue import run_analysis_sync

    run_analysis_sync(analysis_id, chain_id, token_address, depth)
    return analysis_id
