"""SQLAlchemy ORM models.

Persists analysis metadata and results. Never stores private keys, seed phrases
or user credentials — only public on-chain identifiers and derived findings.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Chain(Base):
    __tablename__ = "chains"

    chain_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    native_symbol: Mapped[str] = mapped_column(String(32))
    explorer_url: Mapped[str | None] = mapped_column(String(256), nullable=True)

    tokens: Mapped[list["Token"]] = relationship(back_populates="chain")


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id: Mapped[int] = mapped_column(ForeignKey("chains.chain_id"), index=True)
    address: Mapped[str] = mapped_column(String(42), index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decimals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_supply: Mapped[str | None] = mapped_column(String(80), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(42), nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_verified: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    chain: Mapped[Chain] = relationship(back_populates="tokens")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="token")


class Analysis(Base):
    __tablename__ = "analyses"

    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chain_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(42), index=True)
    token_id: Mapped[int | None] = mapped_column(ForeignKey("tokens.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    analysis_depth: Mapped[str] = mapped_column(String(16), default="standard")
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    risk_classification: Mapped[str | None] = mapped_column(String(48), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    token: Mapped[Token | None] = relationship(back_populates="analyses")
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    findings: Mapped[list["SecurityFinding"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    privileges: Mapped[list["TokenPrivilege"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    tax_results: Mapped[list["TaxResult"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    report: Mapped["SecurityReportRow | None"] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", uselist=False
    )


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.analysis_id"), index=True)
    fork_block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pair_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    router: Mapped[str | None] = mapped_column(String(42), nullable=True)
    buy_success: Mapped[bool | None] = mapped_column(nullable=True)
    sell_success: Mapped[bool | None] = mapped_column(nullable=True)
    scenario_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="simulation_runs")


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.analysis_id"), index=True)
    finding_id: Mapped[str] = mapped_column(String(96))
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analysis: Mapped[Analysis] = relationship(back_populates="findings")


class TokenPrivilege(Base):
    __tablename__ = "token_privileges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.analysis_id"), index=True)
    selector: Mapped[str] = mapped_column(String(96))
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    source_evidence: Mapped[bool | None] = mapped_column(nullable=True)

    analysis: Mapped[Analysis] = relationship(back_populates="privileges")


class TaxResult(Base):
    __tablename__ = "tax_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.analysis_id"), index=True)
    buy_tax_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_tax_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    dynamic: Mapped[bool | None] = mapped_column(nullable=True)
    inconclusive: Mapped[bool | None] = mapped_column(nullable=True)

    analysis: Mapped[Analysis] = relationship(back_populates="tax_results")


class SecurityReportRow(Base):
    __tablename__ = "security_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.analysis_id"), unique=True, index=True)
    report_id: Mapped[str] = mapped_column(String(64), index=True)
    json_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    html_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="report")


# Re-exported for convenience in migrations/scripts.
__all__: list[str] = [
    "Base",
    "Chain",
    "Token",
    "Analysis",
    "SimulationRun",
    "SecurityFinding",
    "TokenPrivilege",
    "TaxResult",
    "SecurityReportRow",
]
