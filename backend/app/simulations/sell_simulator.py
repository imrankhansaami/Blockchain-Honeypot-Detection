"""Sell simulation on an isolated fork.

Approves the router, executes the sell through the fee-on-transfer-supporting
entrypoint, and measures the native currency actually received so that the
effective sell tax can be computed from balance deltas.
"""

from __future__ import annotations

from web3 import Web3

from app.schemas.simulation import TxResult
from app.simulations.abis import ERC20_ABI, ROUTER_ABI
from app.simulations.buy_simulator import _min_out
from app.simulations.executor import TxExecutor


class SellSimulator:
    def __init__(self, executor: TxExecutor) -> None:
        self.executor = executor

    def _deadline(self) -> int:
        return int(self.executor.w3.eth.get_block("latest")["timestamp"]) + 1200

    def quote_native(self, router: str, amount_tokens: int, path: list[str]) -> int | None:
        contract = self.executor.w3.eth.contract(
            address=Web3.to_checksum_address(router), abi=ROUTER_ABI
        )
        try:
            amounts = contract.functions.getAmountsOut(amount_tokens, path).call()
            return int(amounts[-1])
        except Exception:  # noqa: BLE001
            return None

    def approve(self, token: str, owner: str, spender: str, amount: int) -> TxResult:
        contract = self.executor.w3.eth.contract(
            address=Web3.to_checksum_address(token), abi=ERC20_ABI
        )
        data = contract.encode_abi(abi_element_identifier="approve", args=[Web3.to_checksum_address(spender), amount])
        return self.executor.execute({"from": owner, "to": token, "data": data})

    def run(
        self,
        *,
        router: str,
        token: str,
        weth: str,
        wallet: str,
        token_amount: int,
        slippage_bps: int = 0,
    ) -> tuple:
        """Return (approve_result, tx_result, native_received, expected_native_out)."""
        path = [Web3.to_checksum_address(token), Web3.to_checksum_address(weth)]
        expected = self.quote_native(router, token_amount, path)
        amount_out_min = _min_out(expected, slippage_bps)

        approve_result = self.approve(token, wallet, router, token_amount)
        if not approve_result.success:
            return approve_result, TxResult(success=False, error="approve failed", revert_reason=approve_result.revert_reason), 0, expected

        contract = self.executor.w3.eth.contract(
            address=Web3.to_checksum_address(router), abi=ROUTER_ABI
        )
        data = contract.encode_abi(
            abi_element_identifier="swapExactTokensForETHSupportingFeeOnTransferTokens",
            args=[
                token_amount,
                amount_out_min,
                path,
                Web3.to_checksum_address(wallet),
                self._deadline(),
            ],
        )
        before = self.executor.native_balance(wallet)
        result = self.executor.execute(
            {"from": wallet, "to": router, "data": data}
        )
        received = self.executor.native_balance(wallet) - before if result.success else 0
        return approve_result, result, received, expected
