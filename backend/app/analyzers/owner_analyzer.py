"""OwnerPrivilegeAnalyzer: administrative capabilities that can be abused.

The analyzer reports *what an owner can do*, the abuse scenario, and the
evidence, but does not assert malice. Privilege existence is severity-scored by
how much damage it enables, weighted by the strength of the evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.analyzers.base import (
    AnalyzerResult,
    Confidence,
    EvidenceSource,
    FindingCategory,
    Severity,
    make_finding,
)


@dataclass(frozen=True)
class PrivilegeSpec:
    selector: str
    title: str
    category: FindingCategory
    severity: Severity
    why: str
    abuse: str
    recommendation: str
    source_hints: tuple[str, ...] = ()


# Bytecode-selector based privilege catalogue.
PRIVILEGE_SPECS: tuple[PrivilegeSpec, ...] = (
    PrivilegeSpec(
        "mint(address,uint256)",
        "Arbitrary minting capability",
        FindingCategory.MINTING,
        Severity.HIGH,
        "The owner can create new tokens at will, diluting holders and draining liquidity.",
        "Owner mints a large supply and sells it into the pool, collapsing the price.",
        "Confirm the mint is capped, timelocked or renounced.",
        ("mint",),
    ),
    PrivilegeSpec(
        "mint(uint256)",
        "Minting capability (single-argument variant)",
        FindingCategory.MINTING,
        Severity.HIGH,
        "A mint entry point exists that creates tokens without a recipient cap.",
        "Owner inflates supply and dumps into liquidity.",
        "Confirm the mint is capped or renounced.",
        ("mint",),
    ),
    PrivilegeSpec(
        "pause()",
        "Pausable transfers",
        FindingCategory.TRANSFER_RESTRICTION,
        Severity.MEDIUM,
        "The owner can halt all token transfers, freezing every holder.",
        "Owner pauses trading, trapping buyers who cannot sell.",
        "Verify pause limitations and whether holders can still exit.",
        ("pause",),
    ),
    PrivilegeSpec(
        "blacklist(address,bool)",
        "Blacklist control (address,bool)",
        FindingCategory.BLACKLIST,
        Severity.HIGH,
        "The owner can block arbitrary addresses from transferring, including the DEX pair.",
        "Owner blacklists the router/pair or specific sellers to block selling.",
        "Confirm blacklist cannot target the liquidity pair or honest holders.",
        ("blacklist", "blocklist", "banned"),
    ),
    PrivilegeSpec(
        "addBlackList(address)",
        "Blacklist control (add)",
        FindingCategory.BLACKLIST,
        Severity.HIGH,
        "Addresses can be added to a transfer blacklist by the owner.",
        "Owner adds sellers to the blacklist after they buy.",
        "Confirm blacklist scope and removability.",
        ("blacklist", "blocklist"),
    ),
    PrivilegeSpec(
        "setTaxes(uint256,uint256)",
        "Owner-adjustable taxes",
        FindingCategory.TAX,
        Severity.MEDIUM,
        "Buy/sell taxes can be changed by the owner after launch.",
        "Owner raises the sell tax to 100% to trap sellers and extract value.",
        "Check whether tax changes are bounded and timelocked.",
        ("tax", "fee"),
    ),
    PrivilegeSpec(
        "setBuyTax(uint256)",
        "Owner-adjustable buy tax",
        FindingCategory.TAX,
        Severity.MEDIUM,
        "The buy tax is owner-controlled and can be raised arbitrarily.",
        "Owner front-runs buyers with a high buy tax.",
        "Verify the tax is capped.",
        ("tax", "fee"),
    ),
    PrivilegeSpec(
        "setSellTax(uint256)",
        "Owner-adjustable sell tax",
        FindingCategory.TAX,
        Severity.HIGH,
        "The sell tax is owner-controlled and can be raised arbitrarily.",
        "Owner raises the sell tax to near 100% to prevent selling.",
        "Verify the tax is capped and timelocked.",
        ("tax", "fee"),
    ),
    PrivilegeSpec(
        "enableTrading()",
        "Trading can be gated by the owner",
        FindingCategory.TRANSFER_RESTRICTION,
        Severity.MEDIUM,
        "Trading must be enabled by the owner; until then transfers revert.",
        "Owner never enables trading or re-disables it to trap buyers.",
        "Confirm trading cannot be disabled after launch.",
        ("trading", "trade", "swapenable"),
    ),
    PrivilegeSpec(
        "upgradeToAndCall(address,bytes)",
        "Upgrade authority (UUPS/transparent)",
        FindingCategory.UPGRADEABILITY,
        Severity.HIGH,
        "The implementation contract can be replaced by the authorised account.",
        "Owner upgrades to a malicious implementation that adds minting or blocks selling.",
        "Verify the upgrade is behind a timelock/multisig.",
        ("upgrade", "implementation"),
    ),
    PrivilegeSpec(
        "transferOwnership(address)",
        "Ownership is transferable",
        FindingCategory.OWNERSHIP,
        Severity.LOW,
        "Ownership can be handed to any address, including an unverified one.",
        "Ownership is moved to a contract that re-enables malicious powers.",
        "Track the ownership target.",
        ("owner",),
    ),
    PrivilegeSpec(
        "withdrawToken(address)",
        "Owner can withdraw arbitrary ERC-20 tokens",
        FindingCategory.OWNERSHIP,
        Severity.MEDIUM,
        "The owner can sweep any ERC-20 held by the contract, including LP tokens.",
        "Owner withdraws liquidity tokens held by the contract, rugging the pool.",
        "Confirm the contract should not custody LP or user tokens.",
        ("withdraw", "rescue"),
    ),
    PrivilegeSpec(
        "withdrawETH()",
        "Owner can withdraw native currency",
        FindingCategory.OWNERSHIP,
        Severity.MEDIUM,
        "The owner can drain native currency held by the contract.",
        "Owner removes accumulated fees or liquidity ETH.",
        "Confirm the contract legitimately holds native currency.",
        ("withdraw",),
    ),
)


class OwnerPrivilegeAnalyzer:
    """Analyses administrative current capabilities from selectors + source."""

    def __init__(self, source_code: str | None = None) -> None:
        self.source_code = source_code
        self._source_lower = (source_code or "").lower()

    def _source_mentions(self, hints: Iterable[str]) -> bool:
        if not self.source_code:
            return False
        return any(hint.lower() in self._source_lower for hint in hints)

    def analyze(self, detected_functions: dict[str, bool]) -> AnalyzerResult:
        findings = []
        privileges: list[dict] = []

        for spec in PRIVILEGE_SPECS:
            present = detected_functions.get(spec.selector, False)
            source_hit = self._source_mentions(spec.source_hints)
            if not present and not source_hit:
                continue
            # Evidence strength: verified source > bytecode selector.
            if source_hit:
                source = EvidenceSource.SOURCE_CODE
                confidence = Confidence.SUSPICIOUS
            else:
                source = EvidenceSource.BYTECODE
                confidence = Confidence.SUSPICIOUS

            fid = f"owner.{spec.selector.split('(')[0]}_{spec.category.value}"
            findings.append(
                make_finding(
                    fid,
                    spec.title,
                    spec.category,
                    spec.severity,
                    confidence,
                    source,
                    f"{spec.why} Evidence: "
                    + ("verified source contains the relevant logic; " if source_hit else "")
                    + ("function selector present in bytecode." if present else ""),
                    evidence={
                        "selector": spec.selector,
                        "selector_present": present,
                        "source_match": source_hit,
                    },
                    impact=spec.abuse,
                    recommendation=spec.recommendation,
                    references=[spec.selector] if present else [],
                )
            )
            privileges.append(
                {
                    "selector": spec.selector,
                    "title": spec.title,
                    "category": spec.category.value,
                    "severity": spec.severity.value,
                    "source_evidence": source_hit,
                }
            )

        warnings: list[str] = []
        if not self.source_code:
            warnings.append(
                "No verified source available; privileges were inferred from bytecode selectors."
            )

        return AnalyzerResult(
            analyzer="owner",
            findings=findings,
            data={"privileges": privileges, "count": len(privileges)},
            warnings=warnings,
        )
