"""Explicit buy/sell simulation endpoints (single scenario on a fresh fork)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from app.core.chains import UnsupportedChainError, get_chain, resolve_rpc_url
from app.schemas.simulation import SimulationReport
from app.simulations.simulation_runner import SimulationRunner

router = APIRouter(tags=["simulation"])

_DEFAULT_WALLET = "0x0000000000000000000000000000000000009999"


class SimulateRequest(BaseModel):
    chain_id: int
    token_address: str
    amount_wei: int | None = Field(default=None, ge=1)
    block_number: int | None = None
    slippage_bps: int = Field(default=0, ge=0, le=5000)
    wallet: str | None = None


def _run(payload: SimulateRequest, *, sell: bool, label: str) -> SimulationReport:
    try:
        get_chain(payload.chain_id)
    except UnsupportedChainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rpc_url = resolve_rpc_url(payload.chain_id)
    if not rpc_url:
        raise HTTPException(status_code=503, detail=f"No RPC configured for chain {payload.chain_id}")

    runner = SimulationRunner(
        chain_id=payload.chain_id,
        token_address=payload.token_address,
        rpc_url=rpc_url,
        block_number=payload.block_number,
        scenarios=[(label, payload.wallet or _DEFAULT_WALLET, payload.amount_wei or 10**17)],
        sell=sell,
        slippage_bps=payload.slippage_bps,
    )
    return runner.run()


@router.post("/simulate/buy", response_model=SimulationReport)
def simulate_buy(payload: SimulateRequest) -> SimulationReport:
    return _run(payload, sell=False, label="buy")


@router.post("/simulate/sell", response_model=SimulationReport)
def simulate_sell(payload: SimulateRequest) -> SimulationReport:
    return _run(payload, sell=True, label="buy_sell")
