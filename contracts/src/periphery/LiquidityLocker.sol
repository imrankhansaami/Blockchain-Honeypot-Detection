// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @title Liquidity locker.
/// @notice Holds LP tokens for a fixed duration. On-chain proof that liquidity
///         cannot be pulled before `unlockTime` is a meaningful mitigating
///         signal the analyzer can surface.
contract LiquidityLocker {
    using SafeERC20 for IERC20;

    struct Lock {
        address token;
        address owner;
        uint256 amount;
        uint64 unlockTime;
        bool withdrawn;
    }

    mapping(uint256 => Lock) public locks;
    uint256 public lockCount;
    address public immutable beneficiary;

    event Locked(uint256 indexed id, address indexed token, address indexed owner, uint256 amount, uint64 unlockTime);
    event Withdrawn(uint256 indexed id, uint256 amount);

    constructor(address _beneficiary) {
        beneficiary = _beneficiary;
    }

    function lock(address token, uint256 amount, uint64 unlockTime) external returns (uint256 id) {
        require(unlockTime > block.timestamp, "LiquidityLocker: unlock in past");
        require(amount > 0, "LiquidityLocker: zero amount");
        id = lockCount++;
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        locks[id] = Lock({token: token, owner: msg.sender, amount: amount, unlockTime: unlockTime, withdrawn: false});
        emit Locked(id, token, msg.sender, amount, unlockTime);
    }

    function withdraw(uint256 id) external {
        Lock storage entry = locks[id];
        require(!entry.withdrawn, "LiquidityLocker: withdrawn");
        require(block.timestamp >= entry.unlockTime, "LiquidityLocker: still locked");
        entry.withdrawn = true;
        IERC20(entry.token).safeTransfer(entry.owner, entry.amount);
        emit Withdrawn(id, entry.amount);
    }
}
