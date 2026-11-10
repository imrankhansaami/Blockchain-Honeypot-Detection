"""HoneypotDetectionEngine tests (behavioural + static signals)."""

from __future__ import annotations

from app.analyzers.honeypot_detector import HoneypotDetectionEngine
from app.schemas.simulation import ScenarioResult, SimulationReport, TxResult


def _scenario(buy_ok=True, sell_ok=True, revert="Sell not allowed"):
    return ScenarioResult(
        name="medium",
        wallet="0x0000000000000000000000000000000000000001",
        fork_block=1,
        buy_amount_wei=10**17,
        buy_result=TxResult(success=buy_ok),
        sell_result=TxResult(success=sell_ok, revert_reason=None if sell_ok else revert),
    )


def _report(scenarios):
    return SimulationReport(
        performed=True,
        fork_block=1,
        chain_id=1,
        token_address="0x0000000000000000000000000000000000000002",
        scenarios=scenarios,
        buy_success_any=any(s.buy_result.success for s in scenarios),
        sell_success_any=any(s.sell_result and s.sell_result.success for s in scenarios),
    )


def test_can_buy_cannot_sell_is_critical_confirmed():
    result = HoneypotDetectionEngine().analyze(
        simulation=_report([_scenario(sell_ok=False)]), detected_functions={}
    )
    assert result.data["can_buy_cannot_sell"] is True
    finding = next(f for f in result.findings if f.id == "honeypot.cannot_sell")
    assert finding.severity.value == "critical"
    assert finding.confidence.value == "confirmed"
    assert "Sell not allowed" in finding.evidence["sell_revert"]


def test_buy_and_sell_ok_is_informational():
    result = HoneypotDetectionEngine().analyze(
        simulation=_report([_scenario()]), detected_functions={}
    )
    assert result.data["can_buy_cannot_sell"] is False
    assert any(f.id == "honeypot.buy_and_sell_ok" for f in result.findings)


def test_blacklist_selector_produces_suspicious_finding():
    result = HoneypotDetectionEngine().analyze(
        simulation=None, detected_functions={"blacklist(address,bool)": True}
    )
    finding = next(f for f in result.findings if f.id == "honeypot.blacklist_capability")
    assert finding.confidence.value == "suspicious"


def test_no_simulation_is_inconclusive():
    result = HoneypotDetectionEngine().analyze(simulation=None, detected_functions={})
    assert result.inconclusive
    assert any(f.id == "honeypot.simulation_unavailable" for f in result.findings)
