"""TokenAnalyzer: metadata, contract type, ownership and proxy detection.

Everything here is derived from live chain state (or a verified explorer
response). Nothing is inferred from a hardcoded token address list.
"""

from __future__ import annotations

from app.analyzers.abi_utils import (
    decode_address,
    decode_bytes32,
    decode_string_return,
    decode_uint,
    detect_selectors,
    is_valid_address,
)
from app.analyzers.base import (
    AnalyzerResult,
    Confidence,
    EvidenceSource,
    FindingCategory,
    Severity,
    make_finding,
)
from app.core.chains import ChainConfig, DexConfig, get_chain
from app.core.constants import (
    EIP1967_ADMIN_SLOT,
    EIP1967_BEACON_SLOT,
    EIP1967_IMPLEMENTATION_SLOT,
    PROXIABLE_SLOT,
)
from app.core.logging import get_logger
from app.schemas.token import (
    ContractType,
    PairInfo,
    ProxyInfo,
    TokenInfo,
    TokenMetadata,
)
from app.services.explorer import ExplorerClient
from app.services.rpc import RpcClient

logger = get_logger(__name__)

_MINIMAL_ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

_FACTORY_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "a", "type": "address"},
            {"name": "b", "type": "address"},
        ],
        "name": "getPair",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

_PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint112"},
            {"name": "reserve1", "type": "uint112"},
            {"name": "blockTimestampLast", "type": "uint32"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class TokenAnalyzer:
    """Collects token metadata and classifies the contract."""

    def __init__(
        self,
        rpc: RpcClient,
        chain: ChainConfig | None = None,
        explorer: ExplorerClient | None = None,
    ) -> None:
        self.rpc = rpc
        self.explorer = explorer
        self.chain: ChainConfig = chain or get_chain(1)

    # --- raw helpers --------------------------------------------------------

    def _raw(self, address: str, data: str, block=None) -> bytes | None:
        tx = {"to": address, "data": data}
        res = self.rpc.eth_call(tx) if block is None else self.rpc.eth_call(tx, block)
        return res.value if res.success else None

    def _read_metadata(self, address: str) -> TokenMetadata:
        meta = TokenMetadata()
        # name
        raw = self._raw(address, "0x06fdde03")
        name = decode_string_return(raw) if raw else None
        if name is None and raw:
            name = decode_bytes32(raw)
        meta.name = name
        if raw is None:
            meta.errors.append("name() call failed")

        raw = self._raw(address, "0x95d89b41")
        symbol = decode_string_return(raw) if raw else None
        if symbol is None and raw:
            symbol = decode_bytes32(raw)
        meta.symbol = symbol
        if raw is None:
            meta.errors.append("symbol() call failed")

        raw = self._raw(address, "0x313ce567")
        decimals = decode_uint(raw) if raw else None
        meta.decimals = decimals
        if raw is None:
            meta.errors.append("decimals() call failed")

        raw = self._raw(address, "0x18160ddd")
        meta.total_supply = decode_uint(raw) if raw else None
        if raw is None:
            meta.errors.append("totalSupply() call failed")

        meta.metadata_complete = all(
            v is not None for v in (meta.name, meta.symbol, meta.decimals, meta.total_supply)
        )
        return meta

    def _read_owner(self, address: str) -> str | None:
        for selector in ("0x8da5cb5b", "0x893d20e8"):  # owner(), getOwner()
            raw = self._raw(address, selector)
            if raw:
                owner = decode_address(raw)
                if owner:
                    return owner
        return None

    def _detect_proxy(self, address: str) -> ProxyInfo:
        info = ProxyInfo()
        slots = {
            "eip1967_implementation": EIP1967_IMPLEMENTATION_SLOT,
            "eip1967_admin": EIP1967_ADMIN_SLOT,
            "eip1967_beacon": EIP1967_BEACON_SLOT,
            "proxiable": PROXIABLE_SLOT,
        }
        values: dict[str, str] = {}
        for label, slot in slots.items():
            try:
                value = self.rpc.get_storage_at(address, slot)
                values[label] = value
            except Exception as exc:  # noqa: BLE001
                logger.debug("storage read for %s failed: %s", label, exc)

        def _addr(hexword: str) -> str | None:
            if not hexword or int(hexword, 16) == 0:
                return None
            try:
                return self.rpc.w3.to_checksum_address("0x" + hexword[-40:])
            except Exception:  # noqa: BLE001
                return None

        impl = _addr(values.get("eip1967_implementation", "0x0"))
        admin = _addr(values.get("eip1967_admin", "0x0"))
        beacon = _addr(values.get("eip1967_beacon", "0x0"))
        proxiable = _addr(values.get("proxiable", "0x0"))

        if impl:
            info.is_proxy = True
            info.implementation = impl
            info.proxy_type = "eip1967"
            info.detection_methods.append("eip1967_implementation_slot")
        if admin:
            info.admin = admin
            info.detection_methods.append("eip1967_admin_slot")
        if beacon:
            info.is_proxy = True
            info.beacon = beacon
            info.proxy_type = info.proxy_type or "beacon"
            info.detection_methods.append("eip1967_beacon_slot")
        if proxiable and not impl:
            info.is_proxy = True
            info.implementation = proxiable
            info.proxy_type = "proxiable"
            info.detection_methods.append("proxiable_slot")

        # Fallback: implementation() selector
        if not info.is_proxy:
            raw = self._raw(address, "0x5c60da1b")
            fallback_impl = decode_address(raw) if raw else None
            if fallback_impl:
                info.is_proxy = True
                info.implementation = fallback_impl
                info.proxy_type = "custom_implementation_getter"
                info.detection_methods.append("implementation_selector")
        return info

    # --- pairs --------------------------------------------------------------

    def _discover_pairs(self, token_address: str, block_number: int | None) -> list[PairInfo]:
        pairs: list[PairInfo] = []
        for dex in self.chain.dexes:
            if dex.kind != "uniswap_v2":
                continue
            result = self.rpc.read(
                dex.factory, _FACTORY_ABI, "getPair", token_address, self.chain.wrapped_native
            )
            if not result.success or not result.value:
                continue
            pair_addr = self.rpc.w3.to_checksum_address(result.value)
            if int(pair_addr, 16) == 0:
                continue
            info = PairInfo(address=pair_addr, dex_name=dex.name, factory=dex.factory, router=dex.router)
            res = self.rpc.read(pair_addr, _PAIR_ABI, "getReserves")
            token0 = self.rpc.read(pair_addr, _PAIR_ABI, "token0")
            token1 = self.rpc.read(pair_addr, _PAIR_ABI, "token1")
            if token0.success:
                info.token0 = self.rpc.w3.to_checksum_address(token0.value)
            if token1.success:
                info.token1 = self.rpc.w3.to_checksum_address(token1.value)
            if res.success:
                r0, r1, _ = res.value
                is_token0 = info.token0 and info.token0.lower() == token_address.lower()
                info.reserve_token = int(r0 if is_token0 else r1)
                info.reserve_native = int(r1 if is_token0 else r0)
                info.liquidity_native_wei = info.reserve_native
                info.has_liquidity = bool(info.reserve_token and info.reserve_native)
            pairs.append(info)
        return pairs

    # --- main ---------------------------------------------------------------

    def analyze(self, token_address: str, block_number: int | None = None) -> AnalyzerResult:
        findings: list = []
        warnings: list[str] = []
        inconclusive: list[str] = []

        if not is_valid_address(token_address):
            raise ValueError(f"Invalid token address: {token_address}")
        address = self.rpc.w3.to_checksum_address(token_address)

        code = self.rpc.get_code(address)
        bytecode_size = max(0, (len(code) - 2) // 2)
        is_contract = bytecode_size > 0

        if not is_contract:
            findings.append(
                make_finding(
                    "token.not_a_contract",
                    "Address is not a contract",
                    FindingCategory.METADATA,
                    Severity.CRITICAL,
                    Confidence.CONFIRMED,
                    EvidenceSource.ONCHAIN,
                    "The address contains no bytecode on the selected chain.",
                    evidence={"address": address, "chain_id": self.chain.chain_id},
                    recommendation="Verify the token address and chain.",
                )
            )
            info = TokenInfo(
                address=address,
                chain_id=self.chain.chain_id,
                chain_name=self.chain.name,
                is_contract=False,
                bytecode_size=0,
                notes=["No bytecode present at the address."],
            )
            return AnalyzerResult(analyzer="token", findings=findings, data=info.model_dump())

        metadata = self._read_metadata(address)
        owner = self._read_owner(address)
        proxy = self._detect_proxy(address)
        selectors = detect_selectors(code)
        pairs = self._discover_pairs(address, block_number)

        core_erc20 = all(
            selectors.get(name, False)
            for name in ("transfer(address,uint256)", "balanceOf(address)", "totalSupply()")
        )
        erc20_compliant = bool(core_erc20 and metadata.total_supply is not None)

        # verification status
        is_verified: bool | None = None
        verification_source: str | None = None
        if self.explorer and self.chain.supports_explorer_api:
            try:
                src = self.explorer.get_source_code(address)
                if src is not None:
                    is_verified = src.get("verified")
                    verification_source = "explorer_api"
                    if not src.get("verified"):
                        inconclusive.append(
                            "Contract source is not verified on the explorer; source-level "
                            "conclusions cannot be established."
                        )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Explorer lookup failed: {exc}")
        else:
            inconclusive.append("Explorer API not configured; verification status unknown.")

        contract_type = self._classify(
            erc20_compliant=erc20_compliant,
            is_proxy=proxy.is_proxy,
            owner=owner,
            selectors=selectors,
        )

        # --- findings ---
        if not metadata.metadata_complete:
            findings.append(
                make_finding(
                    "token.incomplete_metadata",
                    "Incomplete ERC-20 metadata",
                    FindingCategory.METADATA,
                    Severity.LOW,
                    Confidence.CONFIRMED,
                    EvidenceSource.ONCHAIN,
                    "One or more standard metadata calls (name/symbol/decimals/totalSupply) "
                    "did not return a standard value. This is common in non-standard or "
                    "malicious tokens that break tools relying on ERC-20 metadata.",
                    evidence={"metadata": metadata.model_dump()},
                )
            )

        if not erc20_compliant:
            findings.append(
                make_finding(
                    "token.non_standard_erc20",
                    "Non-standard ERC-20 behaviour",
                    FindingCategory.FUNCTIONALITY,
                    Severity.MEDIUM,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.BYTECODE,
                    "The contract does not expose the expected ERC-20 core selectors and/or "
                    "metadata calls fail. It may implement custom transfer semantics. "
                    "Function names alone are not proof of standard behaviour.",
                    evidence={"core_erc20_selectors": core_erc20, "metadata": metadata.model_dump()},
                )
            )

        if proxy.is_proxy:
            findings.append(
                make_finding(
                    "token.proxy_detected",
                    "Upgradeable / proxy contract detected",
                    FindingCategory.UPGRADEABILITY,
                    Severity.MEDIUM,
                    Confidence.CONFIRMED,
                    EvidenceSource.ONCHAIN,
                    "The contract resolves to an implementation via a known proxy storage slot "
                    "or an implementation() getter. The logic can be replaced after launch.",
                    evidence=proxy.model_dump(),
                    impact="Implementation can be swapped to introduce restrictions or minting.",
                    recommendation="Inspect the proxy admin and upgrade authorisation.",
                )
            )

        if owner:
            findings.append(
                make_finding(
                    "token.owner_present",
                    "Contract has an owner",
                    FindingCategory.OWNERSHIP,
                    Severity.LOW,
                    Confidence.CONFIRMED,
                    EvidenceSource.ONCHAIN,
                    "An owner()/getOwner() call returns a non-zero address. Ownership alone is "
                    "not malicious and is common in legitimate tokens.",
                    evidence={"owner": owner},
                )
            )
        elif metadata.metadata_complete:
            findings.append(
                make_finding(
                    "token.ownership_renounced_or_none",
                    "No owner detected",
                    FindingCategory.OWNERSHIP,
                    Severity.INFO,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.ONCHAIN,
                    "No owner()/getOwner() returned a non-zero address. Ownership may be "
                    "renounced, absent, or exposed under a non-standard getter.",
                    evidence={},
                )
            )

        has_liquidity = any(p.has_liquidity for p in pairs)
        if not pairs:
            findings.append(
                make_finding(
                    "token.no_pair_found",
                    "No DEX pair found on configured factories",
                    FindingCategory.LIQUIDITY,
                    Severity.INFO,
                    Confidence.SUSPICIOUS,
                    EvidenceSource.ONCHAIN,
                    "No V2-style pair exists between this token and the wrapped native token on "
                    "the configured factories. Buy/sell simulation may not be possible.",
                    evidence={"dexes_tried": [d.name for d in self.chain.dexes]},
                )
            )

        info = TokenInfo(
            address=address,
            chain_id=self.chain.chain_id,
            chain_name=self.chain.name,
            is_contract=is_contract,
            bytecode_size=bytecode_size,
            metadata=metadata,
            owner=owner,
            ownership_renounced=(owner == "0x0000000000000000000000000000000000000000") if owner else None,
            is_verified=is_verified,
            verification_source=verification_source,
            proxy=proxy,
            contract_type=contract_type,
            erc20_compliant=erc20_compliant,
            detected_functions=selectors,
            pairs=pairs,
            notes=[f"{len(pairs)} pair(s) discovered"] if pairs else [],
        )
        return AnalyzerResult(
            analyzer="token",
            findings=findings,
            data=info.model_dump(),
            warnings=warnings,
            inconclusive=inconclusive,
        )

    @staticmethod
    def _classify(
        *, erc20_compliant: bool, is_proxy: bool, owner: str | None, selectors: dict[str, bool]
    ) -> ContractType:
        if not erc20_compliant:
            return ContractType.NON_STANDARD
        if is_proxy:
            return ContractType.UPGRADEABLE_ERC20
        privileged = any(
            selectors.get(name, False)
            for name in (
                "mint(address,uint256)",
                "mint(uint256)",
                "pause()",
                "blacklist(address,bool)",
                "setTaxes(uint256,uint256)",
            )
        )
        if owner and privileged:
            return ContractType.OWNABLE_ERC20
        if privileged:
            return ContractType.CUSTOMIZED_TOKEN
        if owner:
            return ContractType.OWNABLE_ERC20
        return ContractType.STANDARD_ERC20
