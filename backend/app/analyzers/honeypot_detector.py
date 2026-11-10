"""HoneypotDetectionEngine.

Combines dynamic simulation evidence with static signals to decide whether a
token permits buying but blocks selling, and to surface blacklist / whitelist /
trading-restriction behaviour. Behavioural (simulation) evidence dominates;
static selectors only ever produce *suspicious* findings.
"""

from __future__ import annotations

from app.analyzers.base import (
    AnalyzerResult,
    Confidence,
    EvidenceSource,
    FindingCategory,
    Severity,
    make_finding,
)
from app.schemas.simulation import SimulationReport


class HoneypotDetectionEngine:
    def __init__(self, source_code: str | None = None) -> None:
        self.source_code = source_code
        self._src = (source_code or "").lower()

    def _src_has(self, *hints: str) -> bool:
        return any(h in self._src for h in hints)

    def analyze(
        self,
        *,
        simulation: SimulationReport | None,
        detected_functions: dict[str, bool],
    ) -> AnalyzerResult:
        findings: list = []
        inconclusive: list[str] = []
        warnings: list[str] = []

        # --- A. Dynamic buy/sell behaviour (authoritative when available) ---
        if simulation and simulation.performed:
            if simulation.buy_success_any and not simulation.sell_success_any:
                reason = self._first_sell_error(simulation)
                findings.append(
                    make_finding(
                        "honeypot.cannot_sell",
                        "Token can be bought but cannot be sold",
                        FindingCategory.HONEYPOT,
                        Severity.CRITICAL,
                        Confidence.CONFIRMED,
                        EvidenceSource.SIMULATION,
                        "An on-fork buy succeeded but every sell attempt reverted. This is the "
                        "defining honeypot behaviour: buyers are trapped.",
                        evidence={
                            "fork_block": simulation.fork_block,
                            "sell_revert": reason,
                            "scenarios": len(simulation.scenarios),
                        },
                        impact="Holders cannot exit; funds are effectively locked.",
                        recommendation="Do not buy this token.",
                    )
                )
            elif not simulation.buy_success_any:
                findings.append(
                    make_finding(
                        "honeypot.cannot_buy",
                        "Buy simulation reverted",
                        FindingCategory.HONEYPOT,
                        Severity.HIGH,
                        Confidence.CONFIRMED,
                        EvidenceSource.SIMULATION,
                        "Every buy attempt on the fork reverted. The token may be paused, "
                        "trading-gated, or otherwise non-tradeable.",
                        evidence={
                            "fork_block": simulation.fork_block,
                            "buy_revert": self._first_buy_error(simulation),
                        },
                        impact="Token may not be tradeable at all.",
                    )
                )
            elif simulation.sell_success_any and simulation.buy_success_any:
                findings.append(
                    make_finding(
                        "honeypot.buy_and_sell_ok",
                        "Buy and sell both succeed on fork",
                        FindingCategory.HONEYPOT,
                        Severity.INFO,
                        Confidence.CONFIRMED,
                        EvidenceSource.SIMULATION,
                        "At least one buy and one sell scenario succeeded on the isolated fork. "
                        "This does not guarantee safety: restrictions may be triggered later by "
                        "the owner or apply to other wallets.",
                        evidence={"fork_block": simulation.fork_block},
                    )
                )
        else:
            reason = simulation.reason if simulation else "Simulation not requested."
            inconclusive.append(f"Dynamic buy/sell behaviour was not established: {reason}")
            findings.append(
                make_finding(
                    "honeypot.simulation_unavailable",
                    "Buy/sell behaviour not simulated",
                    FindingCategory.HONEYPOT,
                    Severity.INFO,
                    Confidence.INCONCLUSIVE,
                    EvidenceSource.BYTECODE,
                    f"Buy/sell simulation could not be performed ({reason}). Conclusions about "
                    "selling ability are therefore inconclusive; static signals below are "
                    "indicative only.",
                    evidence={"simulation": simulation.model_dump() if simulation else None},
                )
            )

        # --- B. Blacklist signals ---
        blacklist_present = detected_functions.get("blacklist(address,bool)", False) or detected_functions.get(
            "addBlackList(address)", False
        )
        if blacklist_present or self._src_has("blacklist", "isblacklisted", "banned"):
            findings.append(
                make_finding(
                    "honeypot.blacklist_capability",
                    "Blacklist capability detected",
                    FindingCategory.BLACKLIST,
                    Severity.HIGH,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE if self._src_has("blacklist") else EvidenceSource.BYTECODE,
                    "A blacklist mechanism exists. It is not automatically malicious, but an "
                    "owner-controlled blacklist can be used to block specific sellers.",
                    evidence={
                        "selectors": {
                            "blacklist(address,bool)": detected_functions.get("blacklist(address,bool)", False),
                            "addBlackList(address)": detected_functions.get("addBlackList(address)", False),
                        },
                        "source_mentions_blacklist": self._src_has("blacklist", "isblacklisted"),
                    },
                    impact="Sellers can be selectively blocked.",
                    recommendation="Confirm who may edit the blacklist and whether the pair is exempt.",
                )
            )

        # --- C. Whitelist / privileged exemptions ---
        if self._src_has("whitelist", "iswhitelisted", "iswhitelisted", "onlywhitelisted"):
            findings.append(
                make_finding(
                    "honeypot.whitelist_capability",
                    "Whitelist / privileged exemptions detected",
                    FindingCategory.WHITELIST,
                    Severity.MEDIUM,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "Transfer logic references whitelisting or privileged exemptions. "
                    "Whitelist-only selling is a common honeypot pattern.",
                    evidence={"source_hint": True},
                    impact="Only privileged wallets may be able to sell.",
                )
            )

        # --- D. Trading restrictions ---
        if detected_functions.get("enableTrading()", False) or self._src_has("tradingenabled", "trading"):
            findings.append(
                make_finding(
                    "honeypot.trading_gate",
                    "Owner-controlled trading gate",
                    FindingCategory.TRANSFER_RESTRICTION,
                    Severity.MEDIUM,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.BYTECODE,
                    "Trading appears gated by an owner-controlled switch. This is often used by "
                    "legitimate launches (anti-bot) but also by honeypots.",
                    evidence={"selector_enableTrading": detected_functions.get("enableTrading()", False)},
                )
            )

        if self._src_has("maxtx", "maxtransaction", "maxwallet", "cooldown", "maxamount"):
            findings.append(
                make_finding(
                    "honeypot.transfer_limits",
                    "Transaction / wallet limits detected",
                    FindingCategory.TRANSFER_RESTRICTION,
                    Severity.LOW,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SOURCE_CODE,
                    "Maximum transaction or wallet limits exist. These are frequently legitimate "
                    "anti-whale controls; they are only concerning if owner-adjustable in a way "
                    "that blocks selling.",
                    evidence={"source_hint": True},
                )
            )

        return AnalyzerResult(
            analyzer="honeypot",
            findings=findings,
            data={
                "can_buy_cannot_sell": bool(
                    simulation
                    and simulation.performed
                    and simulation.buy_success_any
                    and not simulation.sell_success_any
                )
            },
            warnings=warnings,
            inconclusive=inconclusive,
        )

    @staticmethod
    def _first_sell_error(simulation: SimulationReport) -> str | None:
        for scenario in simulation.scenarios:
            if scenario.sell_result and not scenario.sell_result.success:
                return scenario.sell_result.revert_reason or scenario.sell_result.error
        return None

    @staticmethod
    def _first_buy_error(simulation: SimulationReport) -> str | None:
        for scenario in simulation.scenarios:
            if not scenario.buy_result.success:
                return scenario.buy_result.revert_reason or scenario.buy_result.error
        return None
