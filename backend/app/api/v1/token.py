"""Token information endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.analyzers.token_analyzer import TokenAnalyzer
from app.core.chains import UnsupportedChainError, get_chain, resolve_explorer_key, resolve_rpc_url
from app.core.exceptions import RpcUnavailableError
from app.schemas.token import TokenInfo
from app.services.explorer import ExplorerClient
from app.services.rpc import RpcClient

router = APIRouter(tags=["token"])


@router.get("/token/{chain_id}/{address}", response_model=TokenInfo)
def get_token(chain_id: int, address: str) -> TokenInfo:
    try:
        chain = get_chain(chain_id)
    except UnsupportedChainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rpc_url = resolve_rpc_url(chain_id)
    if not rpc_url:
        raise HTTPException(status_code=503, detail=f"No RPC configured for chain {chain_id}")

    explorer = None
    key = resolve_explorer_key(chain_id)
    if key and chain.supports_explorer_api:
        try:
            explorer = ExplorerClient(chain, key)
        except ValueError:
            explorer = None

    try:
        rpc = RpcClient(rpc_url)
        result = TokenAnalyzer(rpc, chain, explorer).analyze(address)
    except RpcUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return TokenInfo.model_validate(result.data)
