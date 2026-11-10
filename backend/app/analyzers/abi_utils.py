"""ABI / bytecode helpers.

Function-selector presence in bytecode is a *heuristic* signal only: it proves a
code path exists near a PUSH4 constant, not that the function is reachable or
what it does. The analyzers label it accordingly.
"""

from __future__ import annotations

from web3 import Web3

from app.core.constants import SELECTORS


def normalize_address(address: str) -> str:
    return Web3.to_checksum_address(address)


def is_valid_address(address: str) -> bool:
    return Web3.is_address(address)


def selector_present(bytecode: str, selector: str) -> bool:
    """Return True if a 4-byte selector constant appears in bytecode."""
    if not bytecode or bytecode in {"0x", "0x0"}:
        return False
    return selector[2:].lower() in bytecode[2:].lower()


def detect_selectors(bytecode: str) -> dict[str, bool]:
    """Map each known selector name to whether it appears in the bytecode."""
    return {name: selector_present(bytecode, sel) for name, sel in SELECTORS.items()}


def decode_string_return(data: bytes) -> str | None:
    """Best-effort decode of a Solidity `string` return value."""
    if not data:
        return None
    try:
        # bytes32 form
        if len(data) == 32:
            return data.rstrip(b"\x00").decode("utf-8", errors="ignore")
        # ABI-encoded dynamic string
        offset = int.from_bytes(data[0:32], "big")
        if offset + 32 > len(data):
            return None
        length = int.from_bytes(data[offset : offset + 32], "big")
        raw = data[offset + 32 : offset + 32 + length]
        return raw.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return None


def decode_bytes32(data: bytes) -> str | None:
    if not data:
        return None
    try:
        return data.rstrip(b"\x00").decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return None


def decode_address(data: bytes) -> str | None:
    if len(data) < 32:
        return None
    try:
        return Web3.to_checksum_address("0x" + data[-20:].hex())
    except Exception:  # noqa: BLE001
        return None


def decode_uint(data: bytes) -> int | None:
    if len(data) < 32:
        return None
    return int.from_bytes(data[:32], "big")
