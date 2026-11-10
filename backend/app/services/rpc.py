"""Web3 RPC client with SSRF hardening, timeouts and graceful failure.

All blockchain reads go through :class:`RpcClient`. It wraps Web3 with a bounded
timeout, bounded retries for transient failures, and rejects any endpoint that
fails SSRF validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from web3 import Web3
from web3.exceptions import ContractLogicError, Web3RPCError
from web3.types import BlockIdentifier

from app.core.config import get_settings
from app.core.exceptions import RpcUnavailableError
from app.core.logging import get_logger
from app.core.security import validate_rpc_url

logger = get_logger(__name__)

# Transient JSON-RPC error markers worth retrying.
_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "connection",
    "temporarily",
    "rate limit",
    "429",
    "502",
    "503",
    "504",
)


def _is_transient(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


@dataclass
class CallResult:
    success: bool
    value: Any = None
    error: str | None = None


class RpcClient:
    """A thin, defensive wrapper around a Web3 HTTP provider."""

    def __init__(self, rpc_url: str, *, allow_private: bool = False) -> None:
        validate_rpc_url(rpc_url, allow_private=allow_private)
        settings = get_settings()
        self.rpc_url = rpc_url
        self._w3 = Web3(
            Web3.HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": settings.rpc_timeout_seconds},
            )
        )
        self._retries = settings.rpc_max_retries

    @property
    def w3(self) -> Web3:
        return self._w3

    def _retry(self, fn, *args, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - classify then re-raise
                last_exc = exc
                if attempt < self._retries and _is_transient(exc):
                    logger.warning("Transient RPC error (attempt %s): %s", attempt + 1, exc)
                    continue
                break
        raise RpcUnavailableError(f"RPC call failed: {last_exc}") from last_exc

    # --- basic chain access -------------------------------------------------

    def is_connected(self) -> bool:
        try:
            return bool(self._retry(self._w3.is_connected))
        except RpcUnavailableError:
            return False

    def chain_id(self) -> int:
        return int(self._retry(lambda: self._w3.eth.chain_id))

    def block_number(self) -> int:
        return int(self._retry(lambda: self._w3.eth.block_number))

    def get_code(self, address: str, block: BlockIdentifier = "latest") -> str:
        return self._retry(
            self._w3.eth.get_code, Web3.to_checksum_address(address), block
        ).to_0x_hex()

    def get_balance(self, address: str, block: BlockIdentifier = "latest") -> int:
        return int(
            self._retry(
                self._w3.eth.get_balance, Web3.to_checksum_address(address), block
            )
        )

    def get_storage_at(
        self, address: str, slot: str, block: BlockIdentifier = "latest"
    ) -> str:
        return self._retry(
            self._w3.eth.get_storage_at,
            Web3.to_checksum_address(address),
            slot,
            block,
        ).to_0x_hex()

    def get_transaction_count(self, address: str) -> int:
        return int(
            self._retry(
                self._w3.eth.get_transaction_count, Web3.to_checksum_address(address)
            )
        )

    # --- contract calls -----------------------------------------------------

    def read(self, address: str, abi: Sequence[dict], function: str, *args) -> CallResult:
        """Call a view/pure function, returning a CallResult rather than raising."""
        try:
            contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(address), abi=list(abi)
            )
            fn = contract.functions[function](*args)
            value = self._retry(fn.call)
            return CallResult(True, value)
        except (ContractLogicError, Web3RPCError) as exc:
            return CallResult(False, error=str(exc))
        except Exception as exc:  # noqa: BLE001
            return CallResult(False, error=str(exc))

    def eth_call(self, tx: dict, block: BlockIdentifier = "latest") -> CallResult:
        try:
            return CallResult(True, self._retry(self._w3.eth.call, tx, block))
        except Exception as exc:  # noqa: BLE001
            return CallResult(False, error=str(exc))
