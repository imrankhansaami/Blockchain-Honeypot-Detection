"""Transaction execution inside an impersonated Anvil environment.

Transactions are sent via ``eth_sendTransaction`` from impersonated, funded
accounts. Revert reasons are captured by first probing with ``eth_call`` so the
report can show why a simulated sell failed.
"""

from __future__ import annotations

from typing import Any

from web3 import Web3

from app.core.logging import get_logger
from app.schemas.simulation import TxResult
from app.simulations.fork_manager import AnvilNode

logger = get_logger(__name__)


def _clean_revert(message: str) -> str:
    # ContractLogicError messages embed the revert reason; keep them readable.
    for marker in ("execution reverted:", "revert", "VM Exception"):
        idx = message.lower().find(marker.lower())
        if idx >= 0:
            return message[idx:].strip()[:300]
    return message.strip()[:300]


class TxExecutor:
    def __init__(self, node: AnvilNode) -> None:
        self.node = node
        self.w3: Web3 = node.w3

    def call(self, tx: dict[str, Any]) -> tuple[bool, Any, str | None]:
        try:
            return True, self.w3.eth.call(tx), None
        except Exception as exc:  # noqa: BLE001
            return False, None, _clean_revert(str(exc))

    def execute(self, tx: dict[str, Any], *, probe: bool = True) -> TxResult:
        """Send a transaction, returning a structured result instead of raising."""
        tx = dict(tx)
        sender = Web3.to_checksum_address(tx["from"])
        self.node.impersonate(sender)
        tx["from"] = sender

        if probe:
            ok, _, reason = self.call(tx)
            if not ok:
                return TxResult(success=False, revert_reason=reason, error=reason)

        try:
            gas = self.w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas * 12 // 10)
        except Exception as exc:  # noqa: BLE001
            return TxResult(
                success=False, revert_reason=_clean_revert(str(exc)), error=str(exc)
            )

        try:
            tx_hash = self.w3.eth.send_transaction(tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        except Exception as exc:  # noqa: BLE001
            return TxResult(success=False, revert_reason=_clean_revert(str(exc)), error=str(exc))

        success = int(receipt.get("status", 0)) == 1
        return TxResult(
            success=success,
            gas_used=int(receipt.get("gasUsed", 0)),
            tx_hash=tx_hash.hex(),
            decoded_log_count=len(receipt.get("logs", [])),
            error=None if success else "transaction reverted",
        )

    def balance_of(self, token: str, account: str) -> int:
        contract = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=_ERC20_BALANCE_ABI)
        return int(contract.functions.balanceOf(Web3.to_checksum_address(account)).call())

    def native_balance(self, account: str) -> int:
        return int(self.w3.eth.get_balance(Web3.to_checksum_address(account)))


_ERC20_BALANCE_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "a", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]
