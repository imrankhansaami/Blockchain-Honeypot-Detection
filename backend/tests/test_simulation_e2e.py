"""End-to-end simulation tests on a hermetic local Anvil.

These prove the simulator performs real buy/sell transactions and measures
taxes, using the Foundry fixtures deployed to a bare Anvil (no external RPC).
"""

from __future__ import annotations

import pytest

from app.simulations.simulation_runner import DexRoute, discover_route, run_scenarios
from tests.local_chain import add_liquidity_eth, deploy, transact

WALLET = "0x000000000000000000000000000000000000bEEF"


def _route(node, chain, dex, token_address):
    route = discover_route(node.w3, chain, token_address)
    assert route is not None, "pair should be discoverable"
    return route


def _run_scenarios(node, chain, token_address, dex, amount=10**17):
    route = discover_route(node.w3, chain, token_address)
    assert route is not None
    return run_scenarios(
        node=node,
        chain=chain,
        token_address=token_address,
        route=route,
        fork_block=node.current_block(),
        scenarios=[("medium", WALLET, amount)],
    )


def test_standard_token_buy_and_sell_succeed(local_node, mock_chain, dex):
    token = deploy(local_node, "StandardERC20", "StandardERC20")
    add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)

    report = _run_scenarios(local_node, mock_chain, token.address, dex)
    assert report.performed
    assert report.buy_success_any
    assert report.sell_success_any
    assert report.can_buy_cannot_sell is False
    # No token tax: effective taxes should be ~0 (only the 0.3% AMM fee is
    # already baked into the quote, so measured tax is near zero).
    assert report.buy_tax_bps is not None and report.buy_tax_bps < 100
    assert report.sell_tax_bps is not None and report.sell_tax_bps < 100


def test_honeypot_can_buy_cannot_sell(local_node, mock_chain, dex):
    token = deploy(local_node, "HoneypotERC20", "HoneypotERC20")
    transact(local_node, token.functions.enableTrading())
    pair = add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    transact(local_node, token.functions.setPair(pair))

    report = _run_scenarios(local_node, mock_chain, token.address, dex)
    assert report.buy_success_any, "buy should succeed"
    assert not report.sell_success_any, "sell should be blocked"
    assert report.can_buy_cannot_sell is True
    # The revert reason should be captured as evidence.
    rev = report.scenarios[0].sell_result.revert_reason
    assert rev and "Sell not allowed" in rev


def test_excessive_sell_tax_detected(local_node, mock_chain, dex):
    token = deploy(local_node, "ExcessiveSellTaxERC20", "ExcessiveSellTaxERC20")
    pair = add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    transact(local_node, token.functions.setPair(pair))

    report = _run_scenarios(local_node, mock_chain, token.address, dex)
    assert report.buy_success_any and report.sell_success_any
    assert report.sell_tax_bps is not None
    assert report.sell_tax_bps > 8000, f"expected ~90% sell tax, got {report.sell_tax_bps}"


def test_adjustable_tax_measures_sell_tax(local_node, mock_chain, dex):
    token = deploy(local_node, "AdjustableTaxERC20", "AdjustableTaxERC20")
    pair = add_liquidity_eth(local_node, dex, token, 100_000 * 10**18, 100 * 10**18)
    transact(local_node, token.functions.setPair(pair))
    transact(local_node, token.functions.setTaxes(0, 1000))  # 10% sell tax

    report = _run_scenarios(local_node, mock_chain, token.address, dex)
    assert report.sell_tax_bps is not None
    assert 800 < report.sell_tax_bps < 1200, f"expected ~10% sell tax, got {report.sell_tax_bps}"


def test_no_liquidity_reports_insufficient(local_node, mock_chain, dex):
    token = deploy(local_node, "NoLiquidityERC20", "NoLiquidityERC20")
    route = discover_route(local_node.w3, mock_chain, token.address)
    assert route is None, "no pair should exist"
