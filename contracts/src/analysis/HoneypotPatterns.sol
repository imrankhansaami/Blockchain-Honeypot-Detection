// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Catalogue of documented honeypot / rug-pull patterns.
/// @notice On-chain, human-readable pattern definitions that mirror the Python
///         detectors. Keeping them in Solidity makes the taxonomy part of the
///         contract suite and usable by on-chain registries or auditors.
library HoneypotPatterns {
    // Stable identifiers, one per detection category.
    bytes32 internal constant CANNOT_SELL = keccak256("CANNOT_SELL");
    bytes32 internal constant TRADING_GATE = keccak256("TRADING_GATE");
    bytes32 internal constant OWNER_BLACKLIST = keccak256("OWNER_BLACKLIST");
    bytes32 internal constant WHITELIST_ONLY = keccak256("WHITELIST_ONLY");
    bytes32 internal constant ADJUSTABLE_SELL_TAX = keccak256("ADJUSTABLE_SELL_TAX");
    bytes32 internal constant EXCESSIVE_TAX = keccak256("EXCESSIVE_TAX");
    bytes32 internal constant UNLIMITED_MINT = keccak256("UNLIMITED_MINT");
    bytes32 internal constant HIDDEN_MINT = keccak256("HIDDEN_MINT");
    bytes32 internal constant OWNER_REBASE = keccak256("OWNER_REBASE");
    bytes32 internal constant UPGRADEABLE_LOGIC = keccak256("UPGRADEABLE_LOGIC");
    bytes32 internal constant MAX_WALLET_TRAP = keccak256("MAX_WALLET_TRAP");
    bytes32 internal constant COOLDOWN_TRAP = keccak256("COOLDOWN_TRAP");
    bytes32 internal constant DRAIN_WITHDRAW = keccak256("DRAIN_WITHDRAW");
    bytes32 internal constant LIQUIDITY_PULL = keccak256("LIQUIDITY_PULL");
    bytes32 internal constant FEE_REDIRECT = keccak256("FEE_REDIRECT");

    /// @notice Severity in basis points of impact (0-10000), for on-chain scoring.
    function severityOf(bytes32 pattern) internal pure returns (uint16) {
        if (pattern == CANNOT_SELL) return 10_000;
        if (pattern == OWNER_BLACKLIST) return 8_500;
        if (pattern == UNLIMITED_MINT || pattern == HIDDEN_MINT) return 8_000;
        if (pattern == ADJUSTABLE_SELL_TAX || pattern == EXCESSIVE_TAX) return 7_500;
        if (pattern == UPGRADEABLE_LOGIC || pattern == DRAIN_WITHDRAW) return 7_000;
        if (pattern == TRADING_GATE || pattern == WHITELIST_ONLY) return 6_000;
        if (pattern == OWNER_REBASE) return 5_500;
        if (pattern == MAX_WALLET_TRAP || pattern == COOLDOWN_TRAP) return 4_000;
        if (pattern == LIQUIDITY_PULL) return 9_000;
        if (pattern == FEE_REDIRECT) return 5_000;
        return 1_000;
    }

    /// @notice Human-readable description of a pattern.
    function describe(bytes32 pattern) internal pure returns (string memory) {
        if (pattern == CANNOT_SELL) return "Buying succeeds but selling reverts for ordinary holders.";
        if (pattern == TRADING_GATE) return "Transfers are gated by an owner-controlled switch.";
        if (pattern == OWNER_BLACKLIST) return "The owner can block arbitrary addresses from transferring.";
        if (pattern == WHITELIST_ONLY) return "Only whitelisted accounts may transfer.";
        if (pattern == ADJUSTABLE_SELL_TAX) return "Sell tax is owner-adjustable after launch.";
        if (pattern == EXCESSIVE_TAX) return "Effective sell tax removes most of the proceeds.";
        if (pattern == UNLIMITED_MINT) return "The owner can mint unbounded supply.";
        if (pattern == HIDDEN_MINT) return "Minting is reachable through an obscured code path.";
        if (pattern == OWNER_REBASE) return "The owner can rebase balances via a multiplier.";
        if (pattern == UPGRADEABLE_LOGIC) return "Implementation logic can be replaced post-deploy.";
        if (pattern == MAX_WALLET_TRAP) return "Owner-set max-wallet limits can block exits.";
        if (pattern == COOLDOWN_TRAP) return "Per-address cooldowns can stall selling.";
        if (pattern == DRAIN_WITHDRAW) return "The owner can withdraw assets held by the contract.";
        if (pattern == LIQUIDITY_PULL) return "Liquidity is unlocked and can be removed at will.";
        if (pattern == FEE_REDIRECT) return "Collected fees can be redirected by the owner.";
        return "Unknown pattern.";
    }
}

/// @title Example token that deliberately combines several honeypot patterns.
/// @notice Reference artifact for the detectors: it gates trading, applies an
///         owner-adjustable sell tax, blocks non-whitelisted sellers, keeps an
///         owner blacklist and allows unlimited minting. Used only in tests.
contract PatternShowcaseToken {
    string public constant name = "Pattern Showcase Token";
    string public constant symbol = "PAT";
    uint8 public constant decimals = 18;

    uint256 public totalSupply;
    address public owner;
    address public pair;
    address public treasury;

    bool public tradingEnabled;
    uint256 public sellTaxBps;
    uint256 public constant MAX_SELL_TAX_BPS = 9000;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => bool) public isBlacklisted;
    mapping(address => bool) public isWhitelisted;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Mint(address indexed to, uint256 value);
    event BlacklistUpdated(address indexed account, bool value);
    event TradingToggled(bool enabled);
    event SellTaxUpdated(uint256 bps);

    modifier onlyOwner() {
        require(msg.sender == owner, "PatternShowcaseToken: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        treasury = msg.sender;
        isWhitelisted[msg.sender] = true;
        _mint(msg.sender, 1_000_000 ether);
    }

    // --- privileged surface (the patterns) ---

    function setPair(address _pair) external onlyOwner {
        pair = _pair;
    }

    function enableTrading() external onlyOwner {
        tradingEnabled = true;
        emit TradingToggled(true);
    }

    function disableTrading() external onlyOwner {
        tradingEnabled = false;
        emit TradingToggled(false);
    }

    function setSellTax(uint256 bps) external onlyOwner {
        require(bps <= MAX_SELL_TAX_BPS, "PatternShowcaseToken: tax too high");
        sellTaxBps = bps;
        emit SellTaxUpdated(bps);
    }

    function setBlacklisted(address account, bool value) external onlyOwner {
        isBlacklisted[account] = value;
        emit BlacklistUpdated(account, value);
    }

    function setWhitelisted(address account, bool value) external onlyOwner {
        isWhitelisted[account] = value;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    function withdrawToken(address token, uint256 amount) external onlyOwner {
        (bool ok, bytes memory data) =
            token.call(abi.encodeWithSelector(0xa9059cbb, treasury, amount));
        require(ok && (data.length == 0 || abi.decode(data, (bool))), "PatternShowcaseToken: withdraw failed");
    }

    // --- ERC-20 surface ---

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        if (allowance[from][msg.sender] != type(uint256).max) {
            allowance[from][msg.sender] -= value;
        }
        _transfer(from, to, value);
        return true;
    }

    function _transfer(address from, address to, uint256 value) internal {
        require(!isBlacklisted[from] && !isBlacklisted[to], "PatternShowcaseToken: blacklisted");
        if (from != address(0) && to != address(0)) {
            require(tradingEnabled, "PatternShowcaseToken: trading disabled");
            if (to == pair && from != owner && !isWhitelisted[from]) {
                revert("PatternShowcaseToken: sell not allowed");
            }
        }
        uint256 fee;
        if (to == pair && pair != address(0)) {
            fee = (value * sellTaxBps) / 10_000;
            if (fee > 0) {
                balanceOf[from] -= fee;
                balanceOf[treasury] += fee;
                emit Transfer(from, treasury, fee);
            }
        }
        balanceOf[from] -= (value - fee);
        balanceOf[to] += (value - fee);
        emit Transfer(from, to, value - fee);
    }

    function _mint(address to, uint256 amount) internal {
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
        emit Mint(to, amount);
    }
}
