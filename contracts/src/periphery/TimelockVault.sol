// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @title Per-user token timelock vault.
/// @notice Users commit tokens for a fixed period. Unlike an owner-controlled
///         locker, nobody — including the deployer — can release early, which is
///         the on-chain evidence of a genuine lock.
contract TimelockVault {
    using SafeERC20 for IERC20;

    struct Lock {
        uint256 amount;
        uint64 unlockTime;
        bool withdrawn;
    }

    IERC20 public immutable token;
    mapping(address => Lock[]) private _locks;

    event Locked(address indexed account, uint256 indexed id, uint256 amount, uint64 unlockTime);
    event Released(address indexed account, uint256 indexed id, uint256 amount);

    constructor(address _token) {
        token = IERC20(_token);
    }

    function lockCount(address account) external view returns (uint256) {
        return _locks[account].length;
    }

    function getLock(address account, uint256 id) external view returns (Lock memory) {
        return _locks[account][id];
    }

    function lock(uint256 amount, uint64 unlockTime) external returns (uint256 id) {
        require(amount > 0, "TimelockVault: zero amount");
        require(unlockTime > block.timestamp, "TimelockVault: unlock in past");
        token.safeTransferFrom(msg.sender, address(this), amount);
        _locks[msg.sender].push(Lock({amount: amount, unlockTime: unlockTime, withdrawn: false}));
        id = _locks[msg.sender].length - 1;
        emit Locked(msg.sender, id, amount, unlockTime);
    }

    function release(uint256 id) external {
        Lock storage entry = _locks[msg.sender][id];
        require(!entry.withdrawn, "TimelockVault: withdrawn");
        require(block.timestamp >= entry.unlockTime, "TimelockVault: still locked");
        entry.withdrawn = true;
        token.safeTransfer(msg.sender, entry.amount);
        emit Released(msg.sender, id, entry.amount);
    }
}
