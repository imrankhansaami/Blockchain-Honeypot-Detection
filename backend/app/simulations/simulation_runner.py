"""Simulation orchestration.

Runs multiple buy/sell scenarios inside a disposable Anvil fork, computes
effective taxes from balance deltas, records evidence, and always tears the fork
down. Never reports a buy/sell as successful unless it actually executed.
"""

from __future__ import annotations

from dataclasses import dataclass

from web3 import Web3

from app.core.chains import ChainConfig, DexConfig, get_chain
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.simulation import ScenarioResult, SimulationReport, TxResult
from app.simulations.abis import FACTORY_ABI, PAIR_ABI, ROUTER_ABI
from app.simulations.buy_simulator import BuySimulator
from app.simulations.executor import TxExecutor
from app.simulations.fork_manager import AnvilNode
from app.simulations.sell_simulator import SellSimulator

logger = get_logger(__name__)


@dataclass
class DexRoute:
    dex: DexConfig
    router: str
    factory: str
    weth: str
    pair: str
    reserve_token: int
    reserve_native: int


def _tax_bps(expected: int | None, received: int | None) -> float | None:
    if not expected or received is None or expected <= 0:
        return None
    return max(0.0, round((1 - received / expected) * 10_000, 2))


def discover_route(w3, chain: ChainConfig, token_address: str) -> DexRoute | None:
    """Find the first V2 pair with liquidity between token and wrapped native."""
    token = Web3.to_checksum_address(token_address)
    for dex in chain.dexes:
        if dex.kind != "uniswap_v2":
            continue
        try:
            factory = w3.eth.contract(address=Web3.to_checksum_address(dex.factory), abi=FACTORY_ABI)
            pair = factory.functions.getPair(token, Web3.to_checksum_address(chain.wrapped_native)).call()
        except Exception as exc:  # noqa: BLE001
            logger.debug("getPair on %s failed: %s", dex.name, exc)
            continue
        if not pair or int(pair, 16) == 0:
            continue
        try:
            pair_c = w3.eth.contract(address=Web3.to_checksum_address(pair), abi=PAIR_ABI)
            token0 = pair_c.functions.token0().call()
            r0, r1, _ = pair_c.functions.getReserves().call()
            is_token0 = Web3.to_checksum_address(token0) == token
            reserve_token = int(r0 if is_token0 else r1)
            reserve_native = int(r1 if is_token0 else r0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("reserve read failed: %s", exc)
            continue
        return DexRoute(
            dex=dex,
            router=dex.router,
            factory=dex.factory,
            weth=chain.wrapped_native,
            pair=Web3.to_checksum_address(pair),
            reserve_token=reserve_token,
            reserve_native=reserve_native,
        )
    return None


def run_scenarios(
    *,
    node: AnvilNode,
    chain: ChainConfig,
    token_address: str,
    route: DexRoute,
    fork_block: int,
    scenarios: list[tuple[str, str, int]],
    slippage_bps: int = 0,
    sell: bool = True,
) -> SimulationReport:
    """Execute scenarios against an already-running node and return a report."""
    executor = TxExecutor(node)
    buy = BuySimulator(executor)
    sell = SellSimulator(executor)

    results: list[ScenarioResult] = []
    for name, wallet, amount_wei in scenarios:
        node.set_balance(wallet, 100 * 10**18)  # plenty of native for gas + swap
        result, received, expected = buy.run(
            router=route.router,
            weth=route.weth,
            token=token_address,
            wallet=wallet,
            amount_wei=amount_wei,
            slippage_bps=slippage_bps,
        )
        scenario = ScenarioResult(
            name=name,
            wallet=Web3.to_checksum_address(wallet),
            fork_block=fork_block,
            buy_amount_wei=amount_wei,
            expected_tokens_out=expected,
            tokens_received=received,
            buy_tax_bps=_tax_bps(expected, received) if result.success else None,
            buy_result=result,
        )

        if result.success and received > 0 and sell:
            # Sell everything received.
            _, sell_result, native_received, expected_native = sell.run(
                router=route.router,
                token=token_address,
                weth=route.weth,
                wallet=wallet,
                token_amount=received,
                slippage_bps=slippage_bps,
            )
            scenario.sell_amount_tokens = received
            scenario.expected_native_out = expected_native
            scenario.native_received_wei = native_received
            scenario.sell_result = sell_result
            scenario.sell_tax_bps = (
                _tax_bps(expected_native, native_received) if sell_result.success else None
            )
        else:
            scenario.notes.append("Sell skipped: buy did not yield tokens.")

        results.append(scenario)

    buy_success = any(s.buy_result.success for s in results)
    sell_success = any(s.sell_result and s.sell_result.success for s in results)
    buy_taxes = [s.buy_tax_bps for s in results if s.buy_result.success and s.buy_tax_bps is not None]
    sell_taxes = [s.sell_tax_bps for s in results if s.sell_result and s.sell_result.success and s.sell_tax_bps is not None]

    return SimulationReport(
        performed=True,
        fork_block=fork_block,
        chain_id=chain.chain_id,
        token_address=Web3.to_checksum_address(token_address),
        pair={
            "address": route.pair,
            "dex": route.dex.name,
            "reserve_token": route.reserve_token,
            "reserve_native_wei": route.reserve_native,
        },
        router=route.router,
        factory=route.factory,
        scenarios=results,
        buy_success_any=buy_success,
        sell_success_any=sell_success,
        buy_tax_bps=round(sum(buy_taxes) / len(buy_taxes), 2) if buy_taxes else None,
        sell_tax_bps=round(sum(sell_taxes) / len(sell_taxes), 2) if sell_taxes else None,
        can_buy_cannot_sell=buy_success and not sell_success,
    )


class SimulationRunner:
    """Sets up a fork and runs the standard scenario matrix."""

    def __init__(
        self,
        *,
        chain_id: int,
        token_address: str,
        rpc_url: str | None,
        block_number: int | None = None,
        scenarios: list[tuple[str, str, int]] | None = None,
        sell: bool = True,
        slippage_bps: int = 0,
    ) -> None:
        self.chain = get_chain(chain_id)
        self.token_address = token_address
        self.rpc_url = rpc_url
        self.block_number = block_number
        self.scenarios = scenarios
        self.sell = sell
        self.slippage_bps = slippage_bps

    def default_scenarios(self) -> list[tuple[str, str, int]]:
        settings = get_settings()
        base = settings.sim_buy_amount_wei
        w1 = "0x0000000000000000000000000000000000001111"
        w2 = "0x0000000000000000000000000000000000002222"
        return [
            ("small", w1, base // 2),
            ("medium", w1, base),
            ("large", w2, base * 5 // 2),
        ]

    def _unavailable(self, reason: str, notes: list[str] | None = None) -> SimulationReport:
        report = SimulationReport(
            performed=False,
            reason=reason,
            chain_id=self.chain.chain_id,
            token_address=self.token_address,
        )
        if notes:
            report.limitations.extend(notes)
        return report

    def run(self) -> SimulationReport:
        settings = get_settings()
        if not settings.simulation_enabled:
            return self._unavailable("Simulation is disabled by configuration.")
        if not self.chain.dexes:
            return self._unavailable("Simulation unavailable: no supported DEX route found.")
        if not self.rpc_url:
            return self._unavailable(
                "Simulation unavailable: no RPC endpoint configured for this chain."
            )

        node = AnvilNode.start(
            fork_url=self.rpc_url,
            fork_block=self.block_number,
            chain_id=self.chain.chain_id,
        )
        try:
            fork_block = node.current_block()
            route = discover_route(node.w3, self.chain, self.token_address)
            if route is None:
                return self._unavailable(
                    "Insufficient liquidity to perform a meaningful buy/sell simulation.",
                    notes=[f"No V2 pair with the wrapped native token on {self.chain.name}."],
                )
            if route.reserve_token <= 0 or route.reserve_native <= 0:
                return self._unavailable(
                    "Insufficient liquidity to perform a meaningful buy/sell simulation.",
                    notes=["Pair exists but reserves are empty."],
                )
            report = run_scenarios(
                node=node,
                chain=self.chain,
                token_address=self.token_address,
                route=route,
                fork_block=fork_block,
                scenarios=self.scenarios or self.default_scenarios(),
                slippage_bps=self.slippage_bps,
                sell=self.sell,
            )
            report.limitations.append(
                f"Simulated against {self.chain.name} state at block {fork_block}. "
                "Behaviour may differ at other blocks or for other wallets."
            )
            return report
        finally:
            node.destroy()


__all__ = [
    "SimulationRunner",
    "run_scenarios",
    "discover_route",
    "DexRoute",
    "TxResult",
]
