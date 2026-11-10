"""Buy simulation on an isolated fork.

Executes a real swap through a Uniswap-V2-compatible router using the
fee-on-transfer-supporting entrypoint (the correct one for taxed tokens), and
measures the tokens actually received.
"""

from __future__ import annotations

from web3 import Web3

from app.simulations.abis import ROUTER_ABI
from app.simulations.executor import TxExecutor


def _min_out(expected: int | None, slippage_bps: int) -> int:
    """Minimum acceptable output for a swap.

    ``slippage_bps == 0`` disables the guard (measurement mode); otherwise the
    guard is the quote reduced by the given tolerance.
    """
    if not expected or slippage_bps <= 0:
        return 0
    return int(expected * (10_000 - slippage_bps) / 10_000)


class BuySimulator:
    def __init__(self, executor: TxExecutor) -> None:
        self.executor = executor

    def _deadline(self) -> int:
        return int(self.executor.w3.eth.get_block("latest")["timestamp"]) + 1200

    def quote(self, router: str, amount_wei: int, path: list[str]) -> int | None:
        contract = self.executor.w3.eth.contract(
            address=Web3.to_checksum_address(router), abi=ROUTER_ABI
        )
        try:
            amounts = contract.functions.getAmountsOut(amount_wei, path).call()
            return int(amounts[-1])
        except Exception:  # noqa: BLE001
            return None

    def run(
        self,
        *,
        router: str,
        weth: str,
        token: str,
        wallet: str,
        amount_wei: int,
        slippage_bps: int = 0,
    ) -> tuple:
        """Return (tx_result, tokens_received, expected_tokens_out).

        When ``slippage_bps`` is 0 the swap runs without a minimum-output guard
        so the *effective tax* can be measured. A non-zero value enforces a
        realistic slippage tolerance instead.
        """
        path = [Web3.to_checksum_address(weth), Web3.to_checksum_address(token)]
        expected = self.quote(router, amount_wei, path)
        amount_out_min = _min_out(expected, slippage_bps)

        contract = self.executor.w3.eth.contract(
            address=Web3.to_checksum_address(router), abi=ROUTER_ABI
        )
        data = contract.encode_abi(
            abi_element_identifier="swapExactETHForTokensSupportingFeeOnTransferTokens",
            args=[amount_out_min, path, Web3.to_checksum_address(wallet), self._deadline()],
        )
        before = self.executor.balance_of(token, wallet)
        result = self.executor.execute(
            {"from": wallet, "to": router, "value": amount_wei, "data": data}
        )
        received = self.executor.balance_of(token, wallet) - before if result.success else 0
        return result, received, expected
