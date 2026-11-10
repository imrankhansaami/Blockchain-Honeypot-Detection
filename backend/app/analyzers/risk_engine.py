"""Explainable risk scoring.

Design principles:
  * correlated findings are de-duplicated by category so a single issue seen
    through several lenses is not counted several times;
  * reproducible behavioural evidence (simulation) outweighs naming heuristics;
  * every point added is traceable to a finding, and the report explains the
    arithmetic;
  * a low score is explicitly *not* proof of safety.
"""

from __future__ import annotations

from collections import defaultdict

from app.analyzers.base import (
    Confidence,
    EvidenceSource,
    Finding,
    FindingCategory,
    Severity,
)
from app.schemas.analysis import RiskAssessment

DISCLAIMER = (
    "This report represents automated security analysis and simulation results. "
    "It is not a formal smart contract audit or a guarantee of token safety. "
    "A low score does not mean the token is safe."
)

# Base points per severity *before* evidence/confidence weighting.
_SEVERITY_POINTS: dict[Severity, float] = {
    Severity.CRITICAL: 60.0,
    Severity.HIGH: 25.0,
    Severity.MEDIUM: 12.0,
    Severity.LOW: 5.0,
    Severity.INFO: 0.0,
}

_CONFIDENCE_FACTOR: dict[Confidence, float] = {
    Confidence.CONFIRMED: 1.0,
    Confidence.SUSPICIOUS: 0.6,
    Confidence.INCONCLUSIVE: 0.25,
}

# Categories treated as independent (not double-counted against one another),
# because they describe genuinely different attack surfaces.
_INDEPENDENT_CATEGORIES = {
    FindingCategory.HONEYPOT,
    FindingCategory.TAX,
    FindingCategory.MINTING,
    FindingCategory.UPGRADEABILITY,
    FindingCategory.BLACKLIST,
    FindingCategory.WHITELIST,
    FindingCategory.ACCESS_CONTROL,
    FindingCategory.TRANSFER_RESTRICTION,
    FindingCategory.LIQUIDITY,
}

_CLASSIFICATIONS: list[tuple[int, str]] = [
    (19, "Low observed risk"),
    (39, "Moderate risk"),
    (59, "Elevated risk"),
    (79, "High risk"),
    (100, "Critical risk"),
]


def classify(score: int) -> str:
    for upper, label in _CLASSIFICATIONS:
        if score <= upper:
            return label
    return "Critical risk"


class RiskEngine:
    """Turns findings into an explainable 0-100 score."""

    def score(
        self,
        findings: list[Finding],
        *,
        uncertainties: list[str] | None = None,
    ) -> RiskAssessment:
        # Contribution per finding.
        contributions: list[tuple[Finding, float]] = []
        for finding in findings:
            base = _SEVERITY_POINTS.get(finding.severity, 0.0)
            if base <= 0:
                continue
            value = base * finding.weight * _CONFIDENCE_FACTOR[finding.confidence]
            contributions.append((finding, round(value, 2)))

        # De-duplicate correlated findings by category: keep the strongest
        # contribution per category. Independent categories are always kept.
        best_by_category: dict[FindingCategory, tuple[Finding, float]] = {}
        for finding, value in contributions:
            current = best_by_category.get(finding.category)
            if current is None or value > current[1]:
                best_by_category[finding.category] = (finding, value)

        total = 0.0
        explanation: list[str] = []
        contributing_ids: list[str] = []
        for category, (finding, value) in sorted(
            best_by_category.items(), key=lambda kv: kv[1][1], reverse=True
        ):
            total += value
            explanation.append(
                f"+{value:g} pts [{finding.severity.value}/{finding.confidence.value}/"
                f"{finding.source.value}] {finding.title}"
            )
            contributing_ids.append(finding.id)

        score = int(min(100, round(total)))
        assessed = classify(score)

        unc = list(uncertainties or [])
        if not findings:
            explanation.append("No scored findings contributed to the risk score.")
        explanation.append(
            "Findings are de-duplicated by category; the strongest finding per category is scored."
        )

        return RiskAssessment(
            score=score,
            classification=assessed,
            explanation=explanation,
            contributing_findings=contributing_ids,
            uncertainties=unc,
            disclaimer=DISCLAIMER,
        )
