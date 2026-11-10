"""Report generation tests (JSON, HTML, PDF)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.analyzers.base import (
    Confidence,
    EvidenceSource,
    FindingCategory,
    Severity,
    make_finding,
)
from app.analyzers.risk_engine import RiskEngine
from app.reports import html_report, json_report, pdf_report
from app.reports.models import SecurityReport
from app.schemas.analysis import AnalysisResult, AnalysisStatus
from app.schemas.token import TokenInfo, TokenMetadata


def _result() -> AnalysisResult:
    findings = [
        make_finding(
            "honeypot.cannot_sell",
            "Token can be bought but cannot be sold",
            FindingCategory.HONEYPOT,
            Severity.CRITICAL,
            Confidence.CONFIRMED,
            EvidenceSource.SIMULATION,
            "Sell reverted on fork.",
            impact="Funds locked.",
            recommendation="Do not buy.",
        )
    ]
    risk = RiskEngine().score(findings)
    token = TokenInfo(
        address="0x0000000000000000000000000000000000000001",
        chain_id=1,
        chain_name="Ethereum Mainnet",
        is_contract=True,
        bytecode_size=5000,
        metadata=TokenMetadata(name="Test", symbol="TST", decimals=18, total_supply=10**24, metadata_complete=True),
    )
    return AnalysisResult(
        analysis_id="abc123",
        chain_id=1,
        token_address=token.address,
        status=AnalysisStatus.COMPLETED,
        block_number=12345,
        token=token,
        findings=findings,
        risk=risk,
    )


def _report() -> SecurityReport:
    return SecurityReport(report_id="abc123", result=_result())


def test_json_report_roundtrips():
    import json

    payload = json_report.generate(_report())
    data = json.loads(payload)
    assert data["result"]["analysis_id"] == "abc123"
    assert data["disclaimer"]


def test_html_report_contains_key_sections():
    html = html_report.render(_report())
    assert "Overall risk" in html
    assert "Token information" in html
    assert "Security findings" in html
    assert "not a formal" in html.lower()


def test_pdf_report_is_valid_pdf():
    data = pdf_report.build(_report())
    assert data[:5] == b"%PDF-"
    assert len(data) > 1000
