// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Bonding deposit with a vesting presale.
/// @notice Participants deposit quote currency for discounted tokens that vest
///         linearly. Models a common (and often abused) launch mechanism.
contract BondingDeposit is Ownable {
    using SafeERC20 for IERC20;

    struct Position {
        uint256 tokens;
        uint256 claimed;
        uint64 start;
        uint64 duration;
    }

    IERC20 public immutable token;
    IERC20 public immutable quote;

    uint256 public tokenPrice; // quote tokens (wei) per 1e18 token units
    uint64 public vestingDuration = 30 days;
    bool public saleOpen;

    mapping(address => Position) public positions;
    uint256 public totalRaised;

    event SaleToggled(bool open);
    event Deposited(address indexed account, uint256 quotePaid, uint256 tokens);
    event Claimed(address indexed account, uint256 tokens);

    constructor(address _token, address _quote, uint256 _tokenPrice) Ownable(msg.sender) {
        token = IERC20(_token);
        quote = IERC20(_quote);
        tokenPrice = _tokenPrice;
    }

    function setSaleOpen(bool open) external onlyOwner {
        saleOpen = open;
        emit SaleToggled(open);
    }

    function setTokenPrice(uint256 price) external onlyOwner {
        tokenPrice = price;
    }

    function setVestingDuration(uint64 duration) external onlyOwner {
        vestingDuration = duration;
    }

    function deposit(uint256 quoteAmount) external returns (uint256 tokensOut) {
        require(saleOpen, "BondingDeposit: sale closed");
        require(quoteAmount > 0, "BondingDeposit: zero");
        tokensOut = (quoteAmount * 1e18) / tokenPrice;
        quote.safeTransferFrom(msg.sender, address(this), quoteAmount);

        Position storage position = positions[msg.sender];
        if (position.tokens == 0) {
            position.start = uint64(block.timestamp);
            position.duration = vestingDuration;
        }
        position.tokens += tokensOut;
        totalRaised += quoteAmount;
        emit Deposited(msg.sender, quoteAmount, tokensOut);
    }

    function claimable(address account) public view returns (uint256) {
        Position storage position = positions[account];
        if (position.tokens == 0) return 0;
        if (block.timestamp >= position.start + position.duration) {
            return position.tokens - position.claimed;
        }
        uint256 vested = (position.tokens * (block.timestamp - position.start)) / position.duration;
        return vested - position.claimed;
    }

    function claim() external {
        uint256 amount = claimable(msg.sender);
        require(amount > 0, "BondingDeposit: nothing to claim");
        positions[msg.sender].claimed += amount;
        token.safeTransfer(msg.sender, amount);
        emit Claimed(msg.sender, amount);
    }

    /// @notice Owner withdraws the raised quote currency.
    function withdrawRaised(address to) external onlyOwner {
        quote.safeTransfer(to, quote.balanceOf(address(this)));
    }
}
