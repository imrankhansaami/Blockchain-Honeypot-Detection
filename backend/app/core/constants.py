"""Well-known selectors, storage slots and topics used during analysis."""

from __future__ import annotations

# --- EIP-1967 standard storage slots ---
EIP1967_IMPLEMENTATION_SLOT = (
    "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)
EIP1967_ADMIN_SLOT = (
    "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
)
EIP1967_BEACON_SLOT = (
    "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
)
# OpenZeppelin / EIP-1822 style implementation slot (PROXIABLE).
PROXIABLE_SLOT = (
    "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876ffce22873"
)

# --- Common ERC-20 / administrative function selectors ---
SELECTORS: dict[str, str] = {
    # ERC-20
    "name()": "0x06fdde03",
    "symbol()": "0x95d89b41",
    "decimals()": "0x313ce567",
    "totalSupply()": "0x18160ddd",
    "balanceOf(address)": "0x70a08231",
    "transfer(address,uint256)": "0xa9059cbb",
    "transferFrom(address,address,uint256)": "0x23b872dd",
    "approve(address,uint256)": "0x095ea7b3",
    "allowance(address,address)": "0xdd62ed3e",
    # Ownership / access control
    "owner()": "0x8da5cb5b",
    "renounceOwnership()": "0x715018a6",
    "transferOwnership(address)": "0xf2fde38b",
    "getOwner()": "0x893d20e8",
    "hasRole(bytes32,address)": "0x91d14854",
    "getRoleAdmin(bytes32)": "0xa217fddf",
    # Supply
    "mint(address,uint256)": "0x40c10f19",
    "mint(uint256)": "0xa0712d68",
    "burn(uint256)": "0x42966c68",
    "burnFrom(address,uint256)": "0x79cc6790",
    # Pause / trading
    "pause()": "0x8456cb59",
    "unpause()": "0x3f4ba83a",
    "paused()": "0x5c975abb",
    "enableTrading()": "0x8a8c523c",
    "disableTrading()": "0x9f7df5e2",
    # Blacklist / whitelist
    "blacklist(address,bool)": "0x1a26a4c5",
    "addBlackList(address)": "0x0ecb93c0",
    "removeBlackList(address)": "0x1ef3c8d5",
    "setBlacklist(address,bool)": "0x1a26a4c5",
    "setWhitelist(address,bool)": "0x5c1c7cfb",
    # Fees
    "setTaxes(uint256,uint256)": "0xb0df75e1",
    "setBuyTax(uint256)": "0x1f2b0ca7",
    "setSellTax(uint256)": "0x7b8f9f36",
    "setFees(uint256,uint256)": "0x8a7a5f1b",
    # Upgradeability
    "upgradeTo(address)": "0x3659cfe6",
    "upgradeToAndCall(address,bytes)": "0x4f1ef286",
    "implementation()": "0x5c60da1b",
    # Financial
    "withdraw()": "0x3ccfd60b",
    "withdrawETH()": "0x4782f779",
    "withdrawToken(address)": "0x89476069",
}

# --- Events (topic0) ---
TOPICS: dict[str, str] = {
    "Transfer": "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
    "Approval": "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
    "OwnershipTransferred": "0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0",
    "Upgraded": "0xbc7cd75a20ee27fd9af8e9d6a6f4b9c8e6a1c2f3f0f4f0b9e9e6d8c1f0c1f0b9e",
    "Paused": "0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258",
    "Unpaused": "0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa",
}

# Identifier substrings used for *heuristic* (non-authoritative) detection.
SUSPICIOUS_NAME_HINTS: dict[str, tuple[str, ...]] = {
    "blacklist": ("blacklist", "blacklisted", "blocklist", "blocked", "banned"),
    "whitelist": ("whitelist", "whitelisted", "wl", "allowedlist", "allowed"),
    "tax": ("tax", "fee", "marketing", "treasury", "devfee"),
    "limits": ("maxtx", "maxtransaction", "maxwallet", "limit", "cooldown"),
    "trading": ("trading", "trade", "open", "launch", "swapenable"),
    "mint": ("mint", "issue", "print", "rebase"),
    "ownership": ("owner", "admin", "operator", "governance", "authority"),
    "upgrade": ("upgrade", "implementation", "proxy", "upgradeto"),
    "exclusion": ("exclude", "excluded", "isExcluded", "flagged", "restricted"),
    "withdraw": ("withdraw", "rescue", "recover", "sweep"),
}
