"""Health and metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.chains import list_chains, resolve_rpc_url
from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    chains = []
    for chain in list_chains():
        chains.append(
            {
                "chain_id": chain.chain_id,
                "name": chain.name,
                "native_symbol": chain.native_symbol,
                "testnet": chain.testnet,
                "rpc_configured": resolve_rpc_url(chain.chain_id) is not None,
                "explorer_api": chain.supports_explorer_api,
                "dexes": [d.name for d in chain.dexes],
            }
        )
    return {
        "status": "ok",
        "environment": settings.environment,
        "simulation_enabled": settings.simulation_enabled,
        "slither_enabled": settings.slither_enabled,
        "chains": chains,
    }


@router.get("/chains")
def chains() -> list[dict]:
    return [
        {
            "chain_id": c.chain_id,
            "name": c.name,
            "native_symbol": c.native_symbol,
            "wrapped_native": c.wrapped_native,
            "wrapped_native_symbol": c.wrapped_native_symbol,
            "explorer_url": c.explorer_url,
            "testnet": c.testnet,
            "dexes": [
                {"name": d.name, "factory": d.factory, "router": d.router, "kind": d.kind}
                for d in c.dexes
            ],
        }
        for c in list_chains()
    ]
