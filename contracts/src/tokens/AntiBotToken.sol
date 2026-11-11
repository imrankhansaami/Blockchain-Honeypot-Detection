// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 16 - Anti-bot token.
/// @notice Applies a per-address cooldown, a max transaction size and a block
///         window in which trading is restricted. These are common, sometimes
///         legitimate launch protections; the analyzer must not treat them as
///         automatically malicious.
contract AntiBotToken is ERC20, Ownable {
    uint256 public maxTxAmount;
    uint256 public cooldownSeconds;
    uint256 public tradingStartBlock;
    mapping(address => uint256) public lastTransferAt;
    mapping(address => bool) public isExempt;

    event LimitsUpdated(uint256 maxTxAmount, uint256 cooldownSeconds);
    event ExemptionSet(address indexed account, bool exempt);

    constructor() ERC20("Anti Bot Token", "ABOT") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
        maxTxAmount = 10_000 ether;
        cooldownSeconds = 30;
        isExempt[msg.sender] = true;
    }

    function setTradingStartBlock(uint256 blockNumber) external onlyOwner {
        tradingStartBlock = blockNumber;
    }

    function setLimits(uint256 _maxTxAmount, uint256 _cooldownSeconds) external onlyOwner {
        maxTxAmount = _maxTxAmount;
        cooldownSeconds = _cooldownSeconds;
        emit LimitsUpdated(_maxTxAmount, _cooldownSeconds);
    }

    function setExempt(address account, bool exempt) external onlyOwner {
        isExempt[account] = exempt;
        emit ExemptionSet(account, exempt);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0) && !isExempt[from] && !isExempt[to]) {
            require(block.number >= tradingStartBlock, "AntiBotToken: trading not open");
            require(value <= maxTxAmount, "AntiBotToken: max tx exceeded");
            require(
                block.timestamp >= lastTransferAt[from] + cooldownSeconds,
                "AntiBotToken: cooldown active"
            );
            lastTransferAt[from] = block.timestamp;
        }
        super._update(from, to, value);
    }
}
