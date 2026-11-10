"""Etherscan-family explorer client (Etherscan, BscScan, ...)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.chains import ChainConfig
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExplorerClient:
    """Minimal read-only client for the Etherscan-compatible v2 API."""

    def __init__(self, chain: ChainConfig, api_key: str, *, timeout: float = 20.0) -> None:
        if not chain.explorer_api_url:
            raise ValueError("Chain does not define an explorer API URL")
        if not api_key:
            raise ValueError("Explorer API key is required")
        self.chain = chain
        self.api_key = api_key
        self.timeout = timeout

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "apikey": self.api_key}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(self.chain.explorer_api_url, params=params)
            resp.raise_for_status()
            return resp.json()

    def get_source_code(self, address: str) -> dict[str, Any] | None:
        """Return verification info for a contract, or None on failure."""
        try:
            data = self._get(
                {"module": "contract", "action": "getsourcecode", "address": address}
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Explorer getsourcecode failed: %s", exc)
            return None

        if str(data.get("status")) != "1" or not data.get("result"):
            return None
        entry = data["result"][0]
        source = entry.get("SourceCode") or ""
        abi = entry.get("ABI") or ""
        verified = bool(source.strip()) and abi not in ("", "Contract source code not verified")
        return {
            "verified": verified,
            "source": source,
            "abi": abi,
            "contract_name": entry.get("ContractName"),
            "compiler_version": entry.get("CompilerVersion"),
            "optimization": entry.get("OptimizationUsed"),
            "proxy": entry.get("Proxy") == "1",
            "implementation": entry.get("Implementation") or None,
        }

    def get_abi(self, address: str) -> str | None:
        try:
            data = self._get({"module": "contract", "action": "getabi", "address": address})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Explorer getabi failed: %s", exc)
            return None
        if str(data.get("status")) != "1":
            return None
        return data.get("result")
