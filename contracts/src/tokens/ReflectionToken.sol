// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 18 - Fee-reward ("reflection") token.
/// @notice A configurable share of every transfer accrues to a reward pool that
///         holders can claim pro-rata. Simplified reflection model for testing
///         holder-reward accounting and owner-adjustable fees.
contract ReflectionToken is ERC20, Ownable {
    uint256 public feeBps = 300;
    uint256 public rewardPool;
    address public pair;

    event FeeUpdated(uint256 feeBps);
    event Claimed(address indexed account, uint256 amount);

    constructor() ERC20("Reflection Token", "RFLX") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function setPair(address _pair) external onlyOwner {
        pair = _pair;
    }

    function setFeeBps(uint256 newFeeBps) external onlyOwner {
        require(newFeeBps <= 1000, "ReflectionToken: fee too high");
        feeBps = newFeeBps;
        emit FeeUpdated(newFeeBps);
    }

    /// @notice Claim a pro-rata share of the accrued reward pool.
    function claim() external returns (uint256 amount) {
        uint256 supply = totalSupply();
        if (supply == 0 || rewardPool == 0) return 0;
        amount = (rewardPool * balanceOf(msg.sender)) / supply;
        require(amount > 0, "ReflectionToken: nothing to claim");
        rewardPool -= amount;
        // Bypass the fee logic so claiming does not re-tax the reward.
        super._update(address(this), msg.sender, amount);
        emit Claimed(msg.sender, amount);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0) && feeBps > 0) {
            uint256 fee = (value * feeBps) / 10_000;
            if (fee > 0) {
                super._update(from, address(this), fee);
                rewardPool += fee;
            }
            super._update(from, to, value - fee);
        } else {
            super._update(from, to, value);
        }
    }
}
