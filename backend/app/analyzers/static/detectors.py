"""Custom token-specific static detectors.

These operate on *verified Solidity source* when available. When source is not
verified they are skipped and the corresponding conclusions are reported as
inconclusive. Every detector implements the same small interface so new rules
can be added without touching the orchestration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.analyzers.base import (
    Confidence,
    EvidenceSource,
    Finding,
    FindingCategory,
    Severity,
    make_finding,
)


@dataclass
class DetectorContext:
    source_code: str
    detected_functions: dict[str, bool]


class BaseDetector:
    name = "base"

    def run(self, ctx: DetectorContext) -> list[Finding]:  # pragma: no cover - interface
        raise NotImplementedError


def _lines_with(source: str, pattern: str, limit: int = 5) -> list[str]:
    out: list[str] = []
    for i, line in enumerate(source.splitlines(), 1):
        if re.search(pattern, line):
            out.append(f"L{i}: {line.strip()[:160]}")
            if len(out) >= limit:
                break
    return out


class ArbitraryMintDetector(BaseDetector):
    name = "arbitrary_mint"

    def run(self, ctx: DetectorContext) -> list[Finding]:
        hits = _lines_with(ctx.source_code, r"function\s+mint\b|_mint\(")
        if not hits:
            return []
        # Distinguish uncapped mints from capped ones heuristically.
        capped = bool(re.search(r"maxSupply|MAX_SUPPLY|capped|cap\b", ctx.source_code))
        return [
            make_finding(
                "static.arbitrary_mint",
                "Mint logic present in source"
                + (" (cap heuristic found)" if capped else " (no obvious cap)"),
                FindingCategory.MINTING,
                Severity.MEDIUM if capped else Severity.HIGH,
                Confidence.SUSPICIOUS,
                EvidenceSource.SOURCE_CODE,
                "Source contains mint logic. Without a hard cap or timelock this enables "
                "supply inflation.",
                evidence={"matches": hits, "cap_heuristic": capped},
                impact="Owner may dilute holders.",
                recommendation="Confirm minting is capped and access-controlled.",
            )
        ]


class TransferConditionDetector(BaseDetector):
    name = "transfer_conditions"

    def run(self, ctx: DetectorContext) -> list[Finding]:
        findings: list[Finding] = []
        # Block-number based restrictions.
        block_hits = _lines_with(ctx.source_code, r"block\.number|block\.timestamp")
        if block_hits and re.search(r"require|revert", ctx.source_code):
            findings.append(
                make_finding(
                    "static.block_restriction",
                    "Transfer logic depends on block number/timestamp",
                    FindingCategory.TRANSFER_RESTRICTION,
                    Severity.MEDIUM,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "Transfers are conditioned on block context. This can implement launch "
                    "windows, cooldowns or time-locked selling.",
                    evidence={"matches": block_hits},
                )
            )
        # Custom transfer override.
        if re.search(r"function\s+_transfer\b|function\s+_update\b", ctx.source_code):
            findings.append(
                make_finding(
                    "static.custom_transfer",
                    "Transfer logic is overridden",
                    FindingCategory.TRANSFER_RESTRICTION,
                    Severity.LOW,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "The token overrides the base transfer logic. This is normal for taxed or "
                    "restricted tokens but warrants inspection.",
                    evidence={"matches": _lines_with(ctx.source_code, r"function\s+_transfer\b|function\s+_update\b")},
                )
            )
        return findings


class RestrictionDetector(BaseDetector):
    name = "restrictions"

    def run(self, ctx: DetectorContext) -> list[Finding]:
        findings: list[Finding] = []
        blacklist = _lines_with(ctx.source_code, r"blacklist|blocklist|banned", limit=3)
        if blacklist:
            findings.append(
                make_finding(
                    "static.blacklist",
                    "Blacklist mapping/function in source",
                    FindingCategory.BLACKLIST,
                    Severity.HIGH,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "Source references a blacklist. Owner-controlled blacklists can block selling.",
                    evidence={"matches": blacklist},
                )
            )
        whitelist = _lines_with(ctx.source_code, r"whitelist|onlyWhitelisted|isWhitelisted", limit=3)
        if whitelist:
            findings.append(
                make_finding(
                    "static.whitelist",
                    "Whitelist logic in source",
                    FindingCategory.WHITELIST,
                    Severity.MEDIUM,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "Source references whitelisting, which can gate who may trade.",
                    evidence={"matches": whitelist},
                )
            )
        return findings


class DangerousCallDetector(BaseDetector):
    name = "dangerous_calls"

    def run(self, ctx: DetectorContext) -> list[Finding]:
        findings: list[Finding] = []
        delegate = _lines_with(ctx.source_code, r"\bdelegatecall\b", limit=3)
        if delegate:
            findings.append(
                make_finding(
                    "static.delegatecall",
                    "delegatecall usage in source",
                    FindingCategory.UPGRADEABILITY,
                    Severity.HIGH,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "delegatecall executes external code in this contract's storage context and "
                    "is a common proxy/honeypot vector.",
                    evidence={"matches": delegate},
                )
            )
        lowlevel = _lines_with(ctx.source_code, r"\.call\{|\.call\(", limit=3)
        if lowlevel:
            findings.append(
                make_finding(
                    "static.low_level_call",
                    "Low-level call in source",
                    FindingCategory.FUNCTIONALITY,
                    Severity.LOW,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "Low-level calls are used; verify they are not used to bypass restrictions.",
                    evidence={"matches": lowlevel},
                )
            )
        return findings


class UnrestrictedAdminDetector(BaseDetector):
    name = "unrestricted_admin"

    _ADMIN_RE = re.compile(
        r"function\s+(setTax\w*|setFee\w*|setMax\w*|blacklist\w*|mint|pause|upgradeTo\w*)\b[^;{]*\{",
        re.IGNORECASE,
    )

    def run(self, ctx: DetectorContext) -> list[Finding]:
        findings: list[Finding] = []
        for m in self._ADMIN_RE.finditer(ctx.source_code):
            snippet = ctx.source_code[m.start() : m.start() + 300]
            guarded = bool(re.search(r"onlyOwner|onlyRole|onlyAdmin|require\(\s*msg\.sender", snippet))
            if not guarded:
                findings.append(
                    make_finding(
                        "static.unrestricted_admin",
                        f"Possibly unrestricted admin function: {m.group(1)}",
                        FindingCategory.ACCESS_CONTROL,
                        Severity.HIGH,
                        Confidence.SUSPICIOUS,
                        EvidenceSource.SOURCE_CODE,
                        "An administrative function does not appear to carry an access-control "
                        "modifier in its first statements. Anyone may be able to call it.",
                        evidence={"function": m.group(1), "snippet": snippet[:160]},
                        recommendation="Verify the access control on this function.",
                    )
                )
        return findings


DEFAULT_DETECTORS: tuple[BaseDetector, ...] = (
    ArbitraryMintDetector(),
    TransferConditionDetector(),
    RestrictionDetector(),
    DangerousCallDetector(),
    UnrestrictedAdminDetector(),
)


def run_detectors(source_code: str | None, detected_functions: dict[str, bool]) -> list[Finding]:
    if not source_code or not source_code.strip():
        return []
    ctx = DetectorContext(source_code=source_code, detected_functions=detected_functions)
    findings: list[Finding] = []
    for detector in DEFAULT_DETECTORS:
        try:
            findings.extend(detector.run(ctx))
        except Exception:  # noqa: BLE001 - a detector must never break the run
            continue
    return findings
