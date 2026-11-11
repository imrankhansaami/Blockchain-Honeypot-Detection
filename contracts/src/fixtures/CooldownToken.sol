// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 25 - Token with per-address cooldowns and a per-block cap.
/// @notice Cooldowns can be legitimate anti-bot protection or a way to stall
///         selling. The analyzer must weigh owner-adjustability when scoring.
contract CooldownToken is ERC20, Ownable {
    uint256 public cooldownSeconds = 60;
    uint256 public maxPerBlock;
    mapping(address => uint256) public lastTransferAt;
    mapping(uint256 => uint256) public transferredInBlock;
    mapping(address => bool) public isExempt;

    event CooldownUpdated(uint256 cooldownSeconds);
    event MaxPerBlockUpdated(uint256 maxPerBlock);

    constructor() ERC20("Cooldown Token", "COOL") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
        maxPerBlock = 100_000 ether;
        isExempt[msg.sender] = true;
    }

    function setCooldown(uint256 seconds_) external onlyOwner {
        cooldownSeconds = seconds_;
        emit CooldownUpdated(seconds_);
    }

    function setMaxPerBlock(uint256 amount) external onlyOwner {
        maxPerBlock = amount;
        emit MaxPerBlockUpdated(amount);
    }

    function setExempt(address account, bool exempt) external onlyOwner {
        isExempt[account] = exempt;
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0) && !isExempt[from]) {
            require(block.timestamp >= lastTransferAt[from] + cooldownSeconds, "CooldownToken: cooldown");
            lastTransferAt[from] = block.timestamp;
            transferredInBlock[block.number] += value;
            require(transferredInBlock[block.number] <= maxPerBlock, "CooldownToken: block cap");
        }
        super._update(from, to, value);
    }
}
