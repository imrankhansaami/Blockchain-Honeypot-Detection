"""Core analysis primitives: findings, severity, confidence and evidence.

Every analyzer emits structured :class:`Finding` objects. A finding never
asserts guilt on its own; it records *what was observed*, *how strongly*, and
*from which evidence source*, so the risk engine and the human reader can weigh
it. This is what keeps the tool from labelling a token a scam on one heuristic.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "informational"


class Confidence(str, Enum):
    """Epistemic status of a finding, not its severity."""

    CONFIRMED = "confirmed"       # reproduced behaviour / authoritative source
    SUSPICIOUS = "suspicious"     # strong indicator, not proven
    INCONCLUSIVE = "inconclusive"  # could not be established either way


class EvidenceSource(str, Enum):
    SIMULATION = "simulation"     # dynamic fork execution (strongest)
    ONCHAIN = "onchain"           # direct chain state / eth_call
    EXPLORER = "explorer"         # verified source from an explorer API
    SOURCE_CODE = "source_code"   # verified Solidity source
    ABI = "abi"                   # contract ABI
    BYTECODE = "bytecode"         # bytecode heuristics
    HEURISTIC = "heuristic"       # naming / pattern matching only (weakest)


# Relative strength of each evidence source, used by the risk engine to weight
# findings. Reproducible behavioural evidence outweighs naming heuristics.
EVIDENCE_WEIGHT: dict[EvidenceSource, float] = {
    EvidenceSource.SIMULATION: 1.0,
    EvidenceSource.ONCHAIN: 0.9,
    EvidenceSource.EXPLORER: 0.7,
    EvidenceSource.SOURCE_CODE: 0.7,
    EvidenceSource.ABI: 0.5,
    EvidenceSource.BYTECODE: 0.4,
    EvidenceSource.HEURISTIC: 0.25,
}


class FindingCategory(str, Enum):
    HONEYPOT = "honeypot"
    TRANSFER_RESTRICTION = "transfer_restriction"
    BLACKLIST = "blacklist"
    WHITELIST = "whitelist"
    TAX = "tax"
    OWNERSHIP = "ownership"
    MINTING = "minting"
    UPGRADEABILITY = "upgradeability"
    LIQUIDITY = "liquidity"
    ACCESS_CONTROL = "access_control"
    FUNCTIONALITY = "functionality"
    METADATA = "metadata"


class Finding(BaseModel):
    """A single structured observation."""

    id: str
    title: str
    category: FindingCategory
    severity: Severity
    confidence: Confidence
    source: EvidenceSource
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    impact: str | None = None
    recommendation: str | None = None
    # Free-form technical pointers (function signature, selector, tx, block...).
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def weight(self) -> float:
        return EVIDENCE_WEIGHT.get(self.source, 0.3)


class AnalyzerResult(BaseModel):
    """Output of a single analyzer."""

    analyzer: str
    findings: list[Finding] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    inconclusive: list[str] = Field(default_factory=list)
    duration_ms: float | None = None


def make_finding(
    fid: str,
    title: str,
    category: FindingCategory,
    severity: Severity,
    confidence: Confidence,
    source: EvidenceSource,
    description: str,
    **kwargs: Any,
) -> Finding:
    """Convenience constructor used throughout the analyzers."""
    return Finding(
        id=fid,
        title=title,
        category=category,
        severity=severity,
        confidence=confidence,
        source=source,
        description=description,
        **kwargs,
    )
