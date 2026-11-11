// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title Simple single-asset staking pool with time-based rewards.
/// @notice A lighter alternative to StakingRewards, used to compare reward
///         accounting and privileged parameter changes.
contract StakingPool is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable stakeToken;
    IERC20 public immutable rewardToken;

    uint256 public rewardPerSecond;
    uint256 public lastUpdate;
    uint256 public accRewardPerShare; // scaled 1e18

    uint256 public totalStaked;
    mapping(address => uint256) public staked;
    mapping(address => uint256) public rewardDebt;
    mapping(address => uint256) public pending;

    event Staked(address indexed account, uint256 amount);
    event Unstaked(address indexed account, uint256 amount);
    event Claimed(address indexed account, uint256 amount);
    event RewardRateUpdated(uint256 rewardPerSecond);

    constructor(address _stakeToken, address _rewardToken, uint256 _rewardPerSecond) Ownable(msg.sender) {
        stakeToken = IERC20(_stakeToken);
        rewardToken = IERC20(_rewardToken);
        rewardPerSecond = _rewardPerSecond;
        lastUpdate = block.timestamp;
    }

    modifier accrue() {
        if (totalStaked > 0) {
            accRewardPerShare += ((block.timestamp - lastUpdate) * rewardPerSecond * 1e18) / totalStaked;
        }
        lastUpdate = block.timestamp;
        _;
    }

    function setRewardPerSecond(uint256 value) external onlyOwner {
        rewardPerSecond = value;
        lastUpdate = block.timestamp;
        emit RewardRateUpdated(value);
    }

    function pendingReward(address account) public view returns (uint256) {
        uint256 acc = accRewardPerShare;
        if (totalStaked > 0) {
            acc += ((block.timestamp - lastUpdate) * rewardPerSecond * 1e18) / totalStaked;
        }
        return pending[account] + (staked[account] * acc) / 1e18 - rewardDebt[account];
    }

    function stake(uint256 amount) external nonReentrant accrue {
        require(amount > 0, "StakingPool: zero");
        pending[msg.sender] = pendingReward(msg.sender);
        staked[msg.sender] += amount;
        totalStaked += amount;
        rewardDebt[msg.sender] = (staked[msg.sender] * accRewardPerShare) / 1e18;
        stakeToken.safeTransferFrom(msg.sender, address(this), amount);
        emit Staked(msg.sender, amount);
    }

    function unstake(uint256 amount) external nonReentrant accrue {
        require(amount > 0 && amount <= staked[msg.sender], "StakingPool: invalid");
        pending[msg.sender] = pendingReward(msg.sender);
        staked[msg.sender] -= amount;
        totalStaked -= amount;
        rewardDebt[msg.sender] = (staked[msg.sender] * accRewardPerShare) / 1e18;
        stakeToken.safeTransfer(msg.sender, amount);
        emit Unstaked(msg.sender, amount);
    }

    function claim() external nonReentrant accrue {
        uint256 reward = pendingReward(msg.sender);
        pending[msg.sender] = 0;
        rewardDebt[msg.sender] = (staked[msg.sender] * accRewardPerShare) / 1e18;
        if (reward > 0) {
            rewardToken.safeTransfer(msg.sender, reward);
            emit Claimed(msg.sender, reward);
        }
    }
}
