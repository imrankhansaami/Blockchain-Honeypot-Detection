"""TaxAnalyzer: effective buy/sell tax derived from real simulation deltas.

Tax is measured from balance differences, never from gas. Where measurement is
not possible the result is explicitly marked inconclusive.
"""

from __future__ import annotations

from statistics import median

from app.analyzers.base import (
    AnalyzerResult,
    Confidence,
    EvidenceSource,
    FindingCategory,
    Severity,
    make_finding,
)
from app.schemas.simulation import SimulationReport


def _tax_bps(expected: int | None, received: int | None) -> float | None:
    if not expected or received is None or expected <= 0:
        return None
    bps = (1 - (received / expected)) * 10_000
    return max(0.0, round(bps, 2))


class TaxAnalyzer:
    def _severity_for_tax(self, bps: float | None) -> tuple[Severity, str]:
        if bps is None:
            return Severity.INFO, "inconclusive"
        if bps >= 5000:
            return Severity.CRITICAL, "critical"
        if bps >= 2000:
            return Severity.HIGH, "high"
        if bps >= 1000:
            return Severity.MEDIUM, "elevated"
        if bps >= 500:
            return Severity.LOW, "noticeable"
        return Severity.INFO, "low"

    def analyze(self, simulation: SimulationReport | None) -> AnalyzerResult:
        findings: list = []
        inconclusive: list[str] = []
        warnings: list[str] = []

        if not simulation or not simulation.performed:
            reason = simulation.reason if simulation else "Simulation not requested."
            inconclusive.append(f"Tax could not be measured: {reason}")
            return AnalyzerResult(
                analyzer="tax",
                findings=findings,
                data={
                    "buy_tax_bps": None,
                    "sell_tax_bps": None,
                    "inconclusive": True,
                    "reason": reason,
                },
                inconclusive=inconclusive,
            )

        buy_taxes = [
            _tax_bps(s.expected_tokens_out, s.tokens_received)
            if s.expected_tokens_out is not None
            else s.buy_tax_bps
            for s in simulation.scenarios
            if s.buy_result.success
        ]
        buy_taxes = [t for t in buy_taxes if t is not None]
        sell_taxes = [
            _tax_bps(s.expected_native_out, s.native_received_wei)
            if s.expected_native_out is not None
            else s.sell_tax_bps
            for s in simulation.scenarios
            if s.sell_result and s.sell_result.success
        ]
        sell_taxes = [t for t in sell_taxes if t is not None]

        buy_tax = round(median(buy_taxes), 2) if buy_taxes else None
        sell_tax = round(median(sell_taxes), 2) if sell_taxes else None

        # Dynamic behaviour: materially different tax across scenarios.
        dynamic = (
            buy_taxes
            and sell_taxes
            and (max(buy_taxes + sell_taxes) - min(buy_taxes + sell_taxes)) > 300
        )

        if buy_tax is not None and buy_tax >= 500:
            severity, label = self._severity_for_tax(buy_tax)
            findings.append(
                make_finding(
                    "tax.buy_tax",
                    f"Effective buy tax {buy_tax / 100:.2f}% ({label})",
                    FindingCategory.TAX,
                    severity,
                    Confidence.CONFIRMED,
                    EvidenceSource.SIMULATION,
                    "Measured from the actual token amount received versus the amount the AMM "
                    "quoted, minus pool fees.",
                    evidence={"buy_tax_bps": buy_tax, "samples": buy_taxes},
                    impact="Buyers pay more than the quoted price.",
                )
            )

        if sell_tax is not None and sell_tax >= 500:
            severity, label = self._severity_for_tax(sell_tax)
            findings.append(
                make_finding(
                    "tax.sell_tax",
                    f"Effective sell tax {sell_tax / 100:.2f}% ({label})",
                    FindingCategory.TAX,
                    severity,
                    Confidence.CONFIRMED,
                    EvidenceSource.SIMULATION,
                    "Measured from the native currency actually received versus the amount the "
                    "AMM quoted, minus pool fees.",
                    evidence={"sell_tax_bps": sell_tax, "samples": sell_taxes},
                    impact="Sellers receive materially less than expected.",
                    recommendation="Treat high sell taxes as an exit risk.",
                )
            )

        if dynamic:
            findings.append(
                make_finding(
                    "tax.dynamic",
                    "Tax varies between scenarios",
                    FindingCategory.TAX,
                    Severity.MEDIUM,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.SIMULATION,
                    "Measured tax differed materially across scenarios, suggesting the tax is "
                    "dynamic, wallet-dependent or size-dependent.",
                    evidence={"buy_samples": buy_taxes, "sell_samples": sell_taxes},
                )
            )

        if buy_tax is None and sell_tax is None:
            inconclusive.append(
                "No successful round trip completed; taxes could not be measured."
            )

        return AnalyzerResult(
            analyzer="tax",
            findings=findings,
            data={
                "buy_tax_bps": buy_tax,
                "sell_tax_bps": sell_tax,
                "dynamic": bool(dynamic),
                "inconclusive": buy_tax is None and sell_tax is None,
                "samples": {"buy": buy_taxes, "sell": sell_taxes},
            },
            warnings=warnings,
            inconclusive=inconclusive,
        )
