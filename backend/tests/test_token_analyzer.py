"""TokenAnalyzer tests using an in-memory fake RPC (no network)."""

from __future__ import annotations

from web3 import Web3

from app.analyzers.token_analyzer import TokenAnalyzer
from app.core.chains import ChainConfig
from app.core.constants import SELECTORS
from app.services.rpc import CallResult

TOKEN = "0x0000000000000000000000000000000000000abc"
OWNER = "0x0000000000000000000000000000000000000def"


def _enc_str(s: str) -> bytes:
    b = s.encode()
    pad = (32 - len(b) % 32) % 32
    return (32).to_bytes(32, "big") + len(b).to_bytes(32, "big") + b + b"\x00" * pad


def _enc_uint(v: int) -> bytes:
    return v.to_bytes(32, "big")


def _enc_addr(a: str) -> bytes:
    return bytes.fromhex(Web3.to_checksum_address(a)[2:].rjust(64, "0"))


def _selector_names(*names: str) -> str:
    body = "60" * 10
    for name in names:
        body += SELECTORS[name][2:]
    return "0x" + body


class FakeRpc:
    def __init__(self, *, bytecode: str, responses: dict[str, bytes], storage: dict[str, str] | None = None):
        self.w3 = Web3()
        self._code = bytecode
        self._responses = responses
        self._storage = storage or {}

    def get_code(self, address: str, block="latest") -> str:
        return self._code

    def eth_call(self, tx: dict, block="latest") -> CallResult:
        data = tx["data"][:10]
        if data in self._responses:
            return CallResult(True, self._responses[data])
        return CallResult(False, error="execution reverted")

    def get_storage_at(self, address: str, slot: str, block="latest") -> str:
        return self._storage.get(slot, "0x" + "00" * 32)

    def read(self, address, abi, function, *args) -> CallResult:
        return CallResult(False, error="no factory")


def _chain() -> ChainConfig:
    return ChainConfig(
        chain_id=1,
        name="Test",
        short_name="test",
        native_symbol="ETH",
        native_decimals=18,
        wrapped_native="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        wrapped_native_symbol="WETH",
        dexes=(),
    )


def _responses() -> dict[str, bytes]:
    return {
        "0x06fdde03": _enc_str("Test Token"),
        "0x95d89b41": _enc_str("TST"),
        "0x313ce567": _enc_uint(18),
        "0x18160ddd": _enc_uint(1_000_000 * 10**18),
        "0x8da5cb5b": _enc_addr(OWNER),
    }


def test_reads_metadata_and_owner():
    bytecode = _selector_names(
        "transfer(address,uint256)", "balanceOf(address)", "totalSupply()", "owner()"
    )
    rpc = FakeRpc(bytecode=bytecode, responses=_responses())
    result = TokenAnalyzer(rpc, _chain()).analyze(TOKEN)
    data = result.data
    assert data["metadata"]["symbol"] == "TST"
    assert data["metadata"]["decimals"] == 18
    assert data["owner"] == Web3.to_checksum_address(OWNER)
    assert data["is_contract"] is True
    assert data["erc20_compliant"] is True


def test_detects_privileged_contract_type():
    bytecode = _selector_names(
        "transfer(address,uint256)", "balanceOf(address)", "totalSupply()", "owner()",
        "mint(address,uint256)",
    )
    rpc = FakeRpc(bytecode=bytecode, responses=_responses())
    result = TokenAnalyzer(rpc, _chain()).analyze(TOKEN)
    assert result.data["contract_type"] == "ownable_erc20"
    assert result.data["detected_functions"]["mint(address,uint256)"] is True


def test_non_standard_token_flagged():
    # Bytecode lacks the core ERC-20 selectors and metadata calls fail.
    rpc = FakeRpc(bytecode="0x60806040", responses={})
    result = TokenAnalyzer(rpc, _chain()).analyze(TOKEN)
    assert result.data["erc20_compliant"] is False
    assert result.data["contract_type"] == "non_standard"
    assert any(f.id == "token.non_standard_erc20" for f in result.findings)


def test_proxy_detection_via_eip1967_slot():
    from app.core.constants import EIP1967_IMPLEMENTATION_SLOT

    impl = "000000000000000000000000" + "11" * 20
    bytecode = _selector_names("transfer(address,uint256)", "balanceOf(address)", "totalSupply()")
    rpc = FakeRpc(
        bytecode=bytecode,
        responses=_responses(),
        storage={EIP1967_IMPLEMENTATION_SLOT: "0x" + impl},
    )
    result = TokenAnalyzer(rpc, _chain()).analyze(TOKEN)
    assert result.data["proxy"]["is_proxy"] is True
    assert result.data["contract_type"] == "upgradeable_erc20"
    assert any(f.id == "token.proxy_detected" for f in result.findings)


def test_not_a_contract():
    rpc = FakeRpc(bytecode="0x", responses={})
    result = TokenAnalyzer(rpc, _chain()).analyze(TOKEN)
    assert result.data["is_contract"] is False
    assert any(f.id == "token.not_a_contract" for f in result.findings)
