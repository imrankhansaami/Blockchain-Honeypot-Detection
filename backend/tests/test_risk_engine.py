"""Risk engine tests: dedupe, weighting and classification."""

from __future__ import annotations

from app.analyzers.base import (
    Confidence,
    EvidenceSource,
    FindingCategory,
    Severity,
    make_finding,
)
from app.analyzers.risk_engine import RiskEngine, classify


def _finding(cat, sev, conf=Confidence.CONFIRMED, source=EvidenceSource.SIMULATION, fid="f"):
    return make_finding(fid, f"{cat.value}/{sev.value}", cat, sev, conf, source, "desc")


def test_score_zero_for_info_only():
    findings = [_finding(FindingCategory.METADATA, Severity.INFO)]
    risk = RiskEngine().score(findings)
    assert risk.score == 0
    assert risk.classification == "Low observed risk"


def test_critical_honeypot_is_high_or_critical():
    findings = [_finding(FindingCategory.HONEYPOT, Severity.CRITICAL)]
    risk = RiskEngine().score(findings)
    assert risk.score >= 60
    assert risk.classification in {"High risk", "Critical risk"}


def test_correlated_findings_are_deduplicated():
    # Three blacklist findings in the same category must count once.
    findings = [
        _finding(FindingCategory.BLACKLIST, Severity.HIGH, fid="a"),
        _finding(FindingCategory.BLACKLIST, Severity.HIGH, fid="b"),
        _finding(FindingCategory.BLACKLIST, Severity.HIGH, fid="c"),
    ]
    risk = RiskEngine().score(findings)
    single = RiskEngine().score([_finding(FindingCategory.BLACKLIST, Severity.HIGH)])
    assert risk.score == single.score
    assert len(risk.contributing_findings) == 1


def test_evidence_weighting_simulation_beats_heuristic():
    sim = [_finding(FindingCategory.TAX, Severity.HIGH, source=EvidenceSource.SIMULATION, fid="s")]
    heur = [_finding(FindingCategory.TAX, Severity.HIGH, source=EvidenceSource.HEURISTIC, fid="h")]
    assert RiskEngine().score(sim).score > RiskEngine().score(heur).score


def test_suspicious_confidence_scores_lower_than_confirmed():
    conf = [_finding(FindingCategory.OWNERSHIP, Severity.HIGH, Confidence.CONFIRMED, fid="c")]
    susp = [_finding(FindingCategory.OWNERSHIP, Severity.HIGH, Confidence.SUSPICIOUS, fid="s")]
    assert RiskEngine().score(conf).score > RiskEngine().score(susp).score


def test_score_capped_at_100():
    findings = [
        _finding(cat, Severity.CRITICAL, fid=f"{cat.value}")
        for cat in [
            FindingCategory.HONEYPOT,
            FindingCategory.TAX,
            FindingCategory.MINTING,
            FindingCategory.UPGRADEABILITY,
        ]
    ]
    assert RiskEngine().score(findings).score == 100


def test_classification_boundaries():
    assert classify(0) == "Low observed risk"
    assert classify(19) == "Low observed risk"
    assert classify(20) == "Moderate risk"
    assert classify(60) == "High risk"
    assert classify(80) == "Critical risk"
    assert classify(100) == "Critical risk"


def test_disclaimer_present():
    risk = RiskEngine().score([_finding(FindingCategory.TAX, Severity.HIGH)])
    assert "not a formal" in risk.disclaimer.lower()
