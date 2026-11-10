"""TaxAnalyzer tests."""

from __future__ import annotations

from app.analyzers.tax_analyzer import TaxAnalyzer
from app.schemas.simulation import ScenarioResult, SimulationReport, TxResult


def _scenario(buy_ok=True, sell_ok=True, expected_tokens=1000, tokens=1000, expected_native=1000, native=1000):
    return ScenarioResult(
        name="medium",
        wallet="0x0000000000000000000000000000000000000001",
        fork_block=100,
        buy_amount_wei=10**17,
        expected_tokens_out=expected_tokens,
        tokens_received=tokens,
        buy_tax_bps=None,
        buy_result=TxResult(success=buy_ok),
        sell_result=TxResult(success=sell_ok) if sell_ok is not None else None,
        expected_native_out=expected_native,
        native_received_wei=native,
    )


def _report(scenarios, performed=True):
    return SimulationReport(
        performed=performed,
        reason=None if performed else "not performed",
        fork_block=100,
        chain_id=1,
        token_address="0x0000000000000000000000000000000000000002",
        scenarios=scenarios,
    )


def test_no_tax_when_received_matches_expected():
    report = _report([_scenario()])
    result = TaxAnalyzer().analyze(report)
    assert result.data["buy_tax_bps"] == 0.0
    assert result.data["sell_tax_bps"] == 0.0


def test_high_sell_tax_detected():
    report = _report([_scenario(expected_native=1000, native=100)])
    result = TaxAnalyzer().analyze(report)
    assert result.data["sell_tax_bps"] == 9000.0
    assert any("sell tax" in f.title.lower() for f in result.findings)


def test_inconclusive_when_not_performed():
    result = TaxAnalyzer().analyze(_report([], performed=False))
    assert result.data["inconclusive"] is True
    assert result.data["buy_tax_bps"] is None
    assert result.inconclusive


def test_failed_sell_yields_no_sell_tax():
    report = _report([_scenario(sell_ok=False)])
    result = TaxAnalyzer().analyze(report)
    assert result.data["sell_tax_bps"] is None


def test_median_across_scenarios():
    report = _report([
        _scenario(expected_native=1000, native=900),
        _scenario(expected_native=1000, native=800),
        _scenario(expected_native=1000, native=850),
    ])
    result = TaxAnalyzer().analyze(report)
    assert result.data["sell_tax_bps"] == 1500.0  # median of 1000,2000,1500 bps
