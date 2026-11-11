// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Linear token vesting with a cliff.
/// @notice A legitimate, auditable use of an owner privilege: funds are locked
///         and released on a schedule, and the owner cannot accelerate them.
contract TokenVesting is Ownable {
    using SafeERC20 for IERC20;

    struct Schedule {
        address beneficiary;
        uint256 total;
        uint256 claimed;
        uint64 start;
        uint64 cliff;
        uint64 duration;
        bool revocable;
        bool revoked;
    }

    mapping(bytes32 => Schedule) private _schedules;

    event ScheduleCreated(bytes32 indexed id, address indexed beneficiary, uint256 total);
    event Released(bytes32 indexed id, address indexed beneficiary, uint256 amount);
    event Revoked(bytes32 indexed id);

    constructor(address initialOwner) Ownable(initialOwner) {}

    function createSchedule(
        bytes32 id,
        address beneficiary,
        uint256 total,
        uint64 start,
        uint64 cliff,
        uint64 duration,
        bool revocable
    ) external onlyOwner {
        require(_schedules[id].beneficiary == address(0), "TokenVesting: exists");
        require(beneficiary != address(0), "TokenVesting: zero beneficiary");
        require(duration > 0 && cliff <= duration, "TokenVesting: bad timings");
        _schedules[id] = Schedule({
            beneficiary: beneficiary,
            total: total,
            claimed: 0,
            start: start,
            cliff: cliff,
            duration: duration,
            revocable: revocable,
            revoked: false
        });
        emit ScheduleCreated(id, beneficiary, total);
    }

    function vestedAmount(bytes32 id) public view returns (uint256) {
        Schedule storage s = _schedules[id];
        if (s.beneficiary == address(0)) return 0;
        if (block.timestamp < s.cliff) return 0;
        if (block.timestamp >= uint256(s.start) + s.duration || s.revoked) return s.total;
        return (s.total * (block.timestamp - s.start)) / s.duration;
    }

    function releasable(bytes32 id) public view returns (uint256) {
        return vestedAmount(id) - _schedules[id].claimed;
    }

    function release(bytes32 id, IERC20 token) external {
        Schedule storage s = _schedules[id];
        uint256 amount = vestedAmount(id) - s.claimed;
        require(amount > 0, "TokenVesting: nothing to release");
        s.claimed += amount;
        token.safeTransfer(s.beneficiary, amount);
        emit Released(id, s.beneficiary, amount);
    }

    function revoke(bytes32 id, IERC20 token) external onlyOwner {
        Schedule storage s = _schedules[id];
        require(s.revocable, "TokenVesting: not revocable");
        require(!s.revoked, "TokenVesting: revoked");
        s.revoked = true;
        uint256 refund = s.total - s.claimed;
        if (refund > 0) {
            token.safeTransfer(owner(), refund);
        }
        emit Revoked(id);
    }
}
