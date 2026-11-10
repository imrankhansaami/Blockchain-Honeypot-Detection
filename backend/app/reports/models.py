"""Report models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.analyzers.risk_engine import DISCLAIMER
from app.schemas.analysis import AnalysisResult


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SecurityReport(BaseModel):
    report_id: str
    generated_at: datetime = Field(default_factory=_now)
    disclaimer: str = DISCLAIMER
    result: AnalysisResult

    @property
    def title(self) -> str:
        token = self.result.token
        symbol = getattr(token, "symbol", None) or getattr(
            getattr(token, "metadata", None), "symbol", None
        )
        return f"Security Report - {symbol or self.result.token_address}"
