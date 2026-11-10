"""Fixture-driven detection tests.

For each behavioural fixture, run a real on-fork buy/sell and assert that the
detection engine and tax analyzer reach the expected conclusion. This is the
"verify the detection engine with the fixtures" requirement.
"""

from __future__ import annotations

from app.analyzers.honeypot_detector import HoneypotDetectionEngine
from app.analyzers.tax_analyzer import TaxAnalyzer
from app.simulations.simulation_runner import discover_route, run_scenarios
from tests.local_chain import add_liquidity_eth, deploy, transact

WALLET = "0x000000000000000000000000000000000000bEEF"


def _simulate(node, chain, token, amount=10**17):
    route = discover_route(node.w3, chain, token.address)
    assert route is not None
    return run_scenarios(
        node=node,
        chain=chain,
        token_address=token.address,
        route=route,
        fork_block=node.current_block(),
        scenarios=[("medium", WALLET, amount)],
    )


def test_standard_fixture_is_not_flagged_as_honeypot(local_node, mock_chain, dex):
    token = deploy(local_node, "StandardERC20", "StandardERC20")
    add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    sim = _simulate(local_node, mock_chain, token)

    honeypot = HoneypotDetectionEngine().analyze(simulation=sim, detected_functions={})
    assert honeypot.data["can_buy_cannot_sell"] is False
    assert not any(f.id == "honeypot.cannot_sell" for f in honeypot.findings)

    tax = TaxAnalyzer().analyze(sim)
    assert tax.data["buy_tax_bps"] is not None and tax.data["buy_tax_bps"] < 100
    assert tax.data["sell_tax_bps"] is not None and tax.data["sell_tax_bps"] < 100


def test_honeypot_fixture_is_flagged(local_node, mock_chain, dex):
    token = deploy(local_node, "HoneypotERC20", "HoneypotERC20")
    transact(local_node, token.functions.enableTrading())
    pair = add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    transact(local_node, token.functions.setPair(pair))
    sim = _simulate(local_node, mock_chain, token)

    honeypot = HoneypotDetectionEngine().analyze(simulation=sim, detected_functions={})
    assert honeypot.data["can_buy_cannot_sell"] is True
    finding = next(f for f in honeypot.findings if f.id == "honeypot.cannot_sell")
    assert finding.severity.value == "critical"
    assert finding.confidence.value == "confirmed"


def test_excessive_sell_tax_fixture(local_node, mock_chain, dex):
    token = deploy(local_node, "ExcessiveSellTaxERC20", "ExcessiveSellTaxERC20")
    pair = add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    transact(local_node, token.functions.setPair(pair))
    sim = _simulate(local_node, mock_chain, token)

    tax = TaxAnalyzer().analyze(sim)
    assert tax.data["sell_tax_bps"] > 8000


def test_adjustable_tax_fixture(local_node, mock_chain, dex):
    token = deploy(local_node, "AdjustableTaxERC20", "AdjustableTaxERC20")
    pair = add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    transact(local_node, token.functions.setPair(pair))
    transact(local_node, token.functions.setTaxes(500, 1500))  # 5% buy, 15% sell
    sim = _simulate(local_node, mock_chain, token)

    tax = TaxAnalyzer().analyze(sim)
    assert 300 < tax.data["buy_tax_bps"] < 700
    assert 1300 < tax.data["sell_tax_bps"] < 1700


def test_fee_on_transfer_fixture_taxed_both_ways(local_node, mock_chain, dex):
    token = deploy(local_node, "FeeOnTransferERC20", "FeeOnTransferERC20")
    add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    sim = _simulate(local_node, mock_chain, token)

    assert sim.buy_success_any and sim.sell_success_any
    tax = TaxAnalyzer().analyze(sim)
    # 5% fee applies on both directions; measured tax should be ~5%.
    assert 300 < tax.data["buy_tax_bps"] < 700
    assert 300 < tax.data["sell_tax_bps"] < 700
