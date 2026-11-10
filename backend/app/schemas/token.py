"""Pydantic schemas for token metadata and contract classification."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ContractType(str, Enum):
    STANDARD_ERC20 = "standard_erc20"
    OWNABLE_ERC20 = "ownable_erc20"
    UPGRADEABLE_ERC20 = "upgradeable_erc20"
    PROXY_TOKEN = "proxy_token"
    CUSTOMIZED_TOKEN = "customized_token"
    NON_STANDARD = "non_standard"
    NOT_ERC20 = "not_erc20"
    UNKNOWN = "unknown"


class TokenMetadata(BaseModel):
    name: str | None = None
    symbol: str | None = None
    decimals: int | None = None
    total_supply: int | None = None
    metadata_complete: bool = False
    errors: list[str] = Field(default_factory=list)


class ProxyInfo(BaseModel):
    is_proxy: bool = False
    proxy_type: str | None = None
    implementation: str | None = None
    admin: str | None = None
    beacon: str | None = None
    detection_methods: list[str] = Field(default_factory=list)


class PairInfo(BaseModel):
    address: str
    dex_name: str
    factory: str
    router: str
    token0: str | None = None
    token1: str | None = None
    reserve_token: int | None = None
    reserve_native: int | None = None
    liquidity_native_wei: int | None = None
    has_liquidity: bool = False


class TokenInfo(BaseModel):
    address: str
    chain_id: int
    chain_name: str
    is_contract: bool
    bytecode_size: int
    metadata: TokenMetadata = Field(default_factory=TokenMetadata)
    owner: str | None = None
    ownership_renounced: bool | None = None
    is_verified: bool | None = None
    verification_source: str | None = None
    proxy: ProxyInfo = Field(default_factory=ProxyInfo)
    contract_type: ContractType = ContractType.UNKNOWN
    erc20_compliant: bool | None = None
    detected_functions: dict[str, bool] = Field(default_factory=dict)
    pairs: list[PairInfo] = Field(default_factory=list)
    creation_block: int | None = None
    notes: list[str] = Field(default_factory=list)
