// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title ERC-20 with voting checkpoints.
/// @notice A self-contained delegation/checkpoint implementation (no external
///         votes library). Holders delegate weight and past voting power is
///         queryable per block, which the analyzer uses to reason about governance.
contract LinearVotingToken is ERC20, Ownable {
    mapping(address => address) public delegates;
    mapping(address => uint256) public nonces;

    struct Checkpoint {
        uint32 fromBlock;
        uint256 votes;
    }

    mapping(address => Checkpoint[]) private _checkpoints;

    event DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate);
    event DelegateVotesChanged(address indexed delegate, uint256 previousVotes, uint256 newVotes);

    constructor() ERC20("Linear Voting Token", "LVT") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function delegate(address delegatee) external {
        _delegate(msg.sender, delegatee);
    }

    function _delegate(address delegator, address delegatee) internal {
        address old = delegates[delegator];
        delegates[delegator] = delegatee;
        emit DelegateChanged(delegator, old, delegatee);
        _moveVotes(old, delegatee, balanceOf(delegator));
    }

    function _moveVotes(address from, address to, uint256 amount) internal {
        if (from != to && amount > 0) {
            if (from != address(0)) {
                uint256 current = votesOf(from);
                _writeCheckpoint(from, current - amount);
                emit DelegateVotesChanged(from, current, current - amount);
            }
            if (to != address(0)) {
                uint256 current = votesOf(to);
                _writeCheckpoint(to, current + amount);
                emit DelegateVotesChanged(to, current, current + amount);
            }
        }
    }

    function _writeCheckpoint(address account, uint256 votes) private {
        Checkpoint[] storage cps = _checkpoints[account];
        uint32 blockNumber = uint32(block.number);
        if (cps.length > 0 && cps[cps.length - 1].fromBlock == blockNumber) {
            cps[cps.length - 1].votes = votes;
        } else {
            cps.push(Checkpoint({fromBlock: blockNumber, votes: votes}));
        }
    }

    function votesOf(address account) public view returns (uint256) {
        Checkpoint[] storage cps = _checkpoints[account];
        return cps.length == 0 ? 0 : cps[cps.length - 1].votes;
    }

    function getPastVotes(address account, uint256 blockNumber) external view returns (uint256) {
        Checkpoint[] storage cps = _checkpoints[account];
        if (cps.length == 0) return 0;
        if (blockNumber >= cps[cps.length - 1].fromBlock) return cps[cps.length - 1].votes;
        for (uint256 i = cps.length; i > 0; i--) {
            if (cps[i - 1].fromBlock <= blockNumber) {
                return cps[i - 1].votes;
            }
        }
        return 0;
    }

    function _update(address from, address to, uint256 value) internal override {
        super._update(from, to, value);
        _moveVotes(delegates[from], delegates[to], value);
    }
}
