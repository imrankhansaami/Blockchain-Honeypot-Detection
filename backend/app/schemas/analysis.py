"""API request/response schemas for analyses and risk assessment."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.analyzers.base import Finding
from app.core.config import AnalysisDepth
from app.schemas.simulation import SimulationReport
from app.schemas.token import TokenInfo


class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeRequest(BaseModel):
    chain_id: int
    token_address: str
    analysis_depth: AnalysisDepth = "standard"
    force_refresh: bool = False

    @field_validator("token_address")
    @classmethod
    def _check_address(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("0x") or len(value) != 42:
            raise ValueError("token_address must be a 0x-prefixed 42-char address")
        return value


class RiskAssessment(BaseModel):
    score: int = Field(ge=0, le=100)
    classification: str
    explanation: list[str] = Field(default_factory=list)
    contributing_findings: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    disclaimer: str


class AnalysisResult(BaseModel):
    analysis_id: str
    chain_id: int
    token_address: str
    status: AnalysisStatus
    analysis_depth: AnalysisDepth = "standard"
    block_number: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: float | None = None
    token: TokenInfo | None = None
    findings: list[Finding] = Field(default_factory=list)
    risk: RiskAssessment | None = None
    simulation: SimulationReport | None = None
    tax: dict | None = None
    owner_analysis: dict | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class AnalysisCreated(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    poll_url: str


class AnalysisSummary(BaseModel):
    analysis_id: str
    chain_id: int
    token_address: str
    status: AnalysisStatus
    risk_score: int | None = None
    risk_classification: str | None = None
    created_at: datetime
