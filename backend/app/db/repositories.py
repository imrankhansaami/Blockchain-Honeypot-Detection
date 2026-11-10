"""Persistence helpers for analyses."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Analysis,
    SecurityFinding,
    SecurityReportRow,
    SimulationRun,
    TaxResult,
    Token,
    TokenPrivilege,
)
from app.schemas.analysis import AnalysisResult, AnalysisStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- reads ---

    def get(self, analysis_id: str) -> Analysis | None:
        return self.session.get(Analysis, analysis_id)

    def get_result(self, analysis_id: str) -> AnalysisResult | None:
        row = self.get(analysis_id)
        if row is None or not row.result_json:
            return None
        return AnalysisResult.model_validate(row.result_json)

    def list_recent(self, limit: int = 20) -> list[Analysis]:
        stmt = select(Analysis).order_by(Analysis.created_at.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars())

    def stats(self) -> dict:
        rows = list(self.session.execute(select(Analysis)).scalars())
        total = len(rows)
        high = sum(1 for r in rows if r.risk_score is not None and r.risk_score >= 60)
        critical = sum(1 for r in rows if r.risk_score is not None and r.risk_score >= 80)
        durations = [r.duration_ms for r in rows if r.duration_ms]
        return {
            "total_analyses": total,
            "high_risk": high,
            "critical_risk": critical,
            "average_duration_ms": round(sum(durations) / len(durations), 2) if durations else None,
        }

    # --- writes ---

    def create_queued(self, analysis_id: str, chain_id: int, address: str, depth: str) -> Analysis:
        row = Analysis(
            analysis_id=analysis_id,
            chain_id=chain_id,
            token_address=address,
            status=AnalysisStatus.QUEUED.value,
            analysis_depth=depth,
        )
        self.session.add(row)
        self.session.commit()
        return row

    def mark_running(self, analysis_id: str) -> None:
        row = self.get(analysis_id)
        if row:
            row.status = AnalysisStatus.RUNNING.value
            self.session.commit()

    def mark_failed(self, analysis_id: str, error: str) -> None:
        row = self.get(analysis_id)
        if row:
            row.status = AnalysisStatus.FAILED.value
            row.error = error[:2000]
            row.finished_at = _utcnow()
            self.session.commit()

    def save_result(self, result: AnalysisResult) -> Analysis:
        row = self.get(result.analysis_id)
        if row is None:
            row = Analysis(
                analysis_id=result.analysis_id,
                chain_id=result.chain_id,
                token_address=result.token_address,
                status=result.status.value,
            )
            self.session.add(row)

        row.status = result.status.value
        row.analysis_depth = result.analysis_depth
        row.block_number = result.block_number
        row.duration_ms = result.duration_ms
        row.result_json = result.model_dump(mode="json")
        row.finished_at = _utcnow()
        if result.risk:
            row.risk_score = result.risk.score
            row.risk_classification = result.risk.classification

        token_id = self._upsert_token(result)
        row.token_id = token_id

        # Replace child rows for idempotency.
        for child in (SecurityFinding, SimulationRun, TokenPrivilege, TaxResult):
            self.session.query(child).filter(child.analysis_id == result.analysis_id).delete()

        for finding in result.findings:
            self.session.add(
                SecurityFinding(
                    analysis_id=result.analysis_id,
                    finding_id=finding.id,
                    title=finding.title,
                    category=finding.category.value,
                    severity=finding.severity.value,
                    confidence=finding.confidence.value,
                    source=finding.source.value,
                    description=finding.description,
                    evidence=finding.evidence,
                )
            )
        if result.simulation and result.simulation.performed:
            self.session.add(
                SimulationRun(
                    analysis_id=result.analysis_id,
                    fork_block=result.simulation.fork_block,
                    pair_address=(result.simulation.pair or {}).get("address"),
                    router=result.simulation.router,
                    buy_success=result.simulation.buy_success_any,
                    sell_success=result.simulation.sell_success_any,
                    scenario_json=result.simulation.model_dump(mode="json"),
                )
            )
        if result.owner_analysis:
            for priv in result.owner_analysis.get("privileges", []):
                self.session.add(
                    TokenPrivilege(
                        analysis_id=result.analysis_id,
                        selector=priv.get("selector", ""),
                        title=priv.get("title", ""),
                        category=priv.get("category", ""),
                        severity=priv.get("severity", ""),
                        source_evidence=priv.get("source_evidence"),
                    )
                )
        if result.tax:
            self.session.add(
                TaxResult(
                    analysis_id=result.analysis_id,
                    buy_tax_bps=result.tax.get("buy_tax_bps"),
                    sell_tax_bps=result.tax.get("sell_tax_bps"),
                    dynamic=result.tax.get("dynamic"),
                    inconclusive=result.tax.get("inconclusive"),
                )
            )

        self.session.commit()
        return row

    def attach_report(self, analysis_id: str, report_id: str, paths: dict[str, str | None]) -> None:
        existing = self.session.execute(
            select(SecurityReportRow).where(SecurityReportRow.analysis_id == analysis_id)
        ).scalar_one_or_none()
        if existing is None:
            existing = SecurityReportRow(analysis_id=analysis_id, report_id=report_id)
            self.session.add(existing)
        existing.json_path = paths.get("json")
        existing.html_path = paths.get("html")
        existing.pdf_path = paths.get("pdf")
        self.session.commit()

    def _upsert_token(self, result: AnalysisResult) -> int | None:
        token = result.token
        if token is None:
            return None
        stmt = select(Token).where(
            Token.chain_id == result.chain_id, Token.address == result.token_address
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            row = Token(chain_id=result.chain_id, address=result.token_address)
            self.session.add(row)
        row.name = token.metadata.name
        row.symbol = token.metadata.symbol
        row.decimals = token.metadata.decimals
        row.total_supply = str(token.metadata.total_supply) if token.metadata.total_supply is not None else None
        row.owner = token.owner
        row.contract_type = token.contract_type.value
        row.is_verified = token.is_verified
        self.session.flush()
        return row.id
