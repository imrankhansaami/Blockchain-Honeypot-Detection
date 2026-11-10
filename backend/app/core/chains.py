"""Chain registry.

Each supported EVM chain is described declaratively so that new chains can be
added without touching analyzer code. RPC endpoints are *never* hardcoded; they
are resolved from environment variables at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import get_settings


@dataclass(frozen=True)
class DexConfig:
    """A DEX deployment on a chain."""

    name: str
    factory: str
    router: str
    # "uniswap_v2" is the only fully supported flavour for now.
    kind: str = "uniswap_v2"


@dataclass(frozen=True)
class ChainConfig:
    chain_id: int
    name: str
    short_name: str
    native_symbol: str
    native_decimals: int
    wrapped_native: str
    wrapped_native_symbol: str
    dexes: tuple[DexConfig, ...] = ()
    explorer_url: str = ""
    explorer_api_url: str = ""
    # Name of the Settings attribute that holds this chain's RPC URL.
    rpc_settings_attr: str = ""
    # Name of the Settings attribute holding the explorer API key.
    explorer_key_settings_attr: str = ""
    supports_explorer_api: bool = False
    testnet: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)


_UNISWAP_V2 = DexConfig(
    name="Uniswap V2",
    factory="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    router="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
)
_PANCAKE_V2 = DexConfig(
    name="PancakeSwap V2",
    factory="0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
    router="0x10ED43C718714eb63d5aA57B78B54704E256024E",
)
_PANCAKE_TESTNET = DexConfig(
    name="PancakeSwap Testnet",
    factory="0x6725F303b657a9451d8BA641348b6761A6CC7a17",
    router="0xD99D1c33F9fC3444f8101754aBC46c52416550D1",
)


CHAINS: dict[int, ChainConfig] = {
    1: ChainConfig(
        chain_id=1,
        name="Ethereum Mainnet",
        short_name="ethereum",
        native_symbol="ETH",
        native_decimals=18,
        wrapped_native="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        wrapped_native_symbol="WETH",
        dexes=(_UNISWAP_V2,),
        explorer_url="https://etherscan.io",
        explorer_api_url="https://api.etherscan.io/api",
        rpc_settings_attr="mainnet_rpc_url",
        explorer_key_settings_attr="etherscan_api_key",
        supports_explorer_api=True,
        tags=("mainnet", "ethereum"),
    ),
    11155111: ChainConfig(
        chain_id=11155111,
        name="Ethereum Sepolia",
        short_name="sepolia",
        native_symbol="ETH",
        native_decimals=18,
        wrapped_native="0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14",
        wrapped_native_symbol="WETH",
        dexes=(
            DexConfig(
                name="Uniswap V2 (Sepolia)",
                factory="0xF62c03E08ada871A0bEb309762E260a7a6a880E6",
                router="0xC532a74256D3Db42D0Bf7a0400fEFDbad7694008",
            ),
        ),
        explorer_url="https://sepolia.etherscan.io",
        explorer_api_url="https://api-sepolia.etherscan.io/api",
        rpc_settings_attr="sepolia_rpc_url",
        explorer_key_settings_attr="etherscan_api_key",
        supports_explorer_api=True,
        testnet=True,
        tags=("sepolia", "ethereum", "testnet"),
    ),
    56: ChainConfig(
        chain_id=56,
        name="BNB Smart Chain",
        short_name="bsc",
        native_symbol="BNB",
        native_decimals=18,
        wrapped_native="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        wrapped_native_symbol="WBNB",
        dexes=(_PANCAKE_V2,),
        explorer_url="https://bscscan.com",
        explorer_api_url="https://api.bscscan.com/api",
        rpc_settings_attr="bsc_rpc_url",
        explorer_key_settings_attr="bscscan_api_key",
        supports_explorer_api=True,
        tags=("bsc", "binance"),
    ),
    97: ChainConfig(
        chain_id=97,
        name="BNB Smart Chain Testnet",
        short_name="bsc_testnet",
        native_symbol="tBNB",
        native_decimals=18,
        wrapped_native="0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd",
        wrapped_native_symbol="WBNB",
        dexes=(_PANCAKE_TESTNET,),
        explorer_url="https://testnet.bscscan.com",
        explorer_api_url="https://api-testnet.bscscan.com/api",
        rpc_settings_attr="bsc_testnet_rpc_url",
        explorer_key_settings_attr="bscscan_api_key",
        supports_explorer_api=True,
        testnet=True,
        tags=("bsc", "testnet"),
    ),
}


class UnsupportedChainError(KeyError):
    """Raised when a chain ID is not configured."""


def get_chain(chain_id: int) -> ChainConfig:
    try:
        return CHAINS[chain_id]
    except KeyError as exc:  # pragma: no cover - trivial
        raise UnsupportedChainError(
            f"Chain {chain_id} is not configured. Supported: {sorted(CHAINS)}"
        ) from exc


def list_chains() -> list[ChainConfig]:
    return list(CHAINS.values())


def resolve_rpc_url(chain_id: int) -> str | None:
    """Return the configured RPC URL for a chain, or None if unset."""
    chain = get_chain(chain_id)
    if not chain.rpc_settings_attr:
        return None
    value = getattr(get_settings(), chain.rpc_settings_attr, "") or ""
    return value.strip() or None


def resolve_explorer_key(chain_id: int) -> str | None:
    chain = get_chain(chain_id)
    if not chain.explorer_key_settings_attr:
        return None
    value = getattr(get_settings(), chain.explorer_key_settings_attr, "") or ""
    return value.strip() or None
