"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.repositories import AnalysisRepository
from app.db.session import get_session


def repo_dependency() -> Iterator[AnalysisRepository]:
    for session in get_session():
        yield AnalysisRepository(session)


__all__ = ["repo_dependency", "Session"]
