// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title Simplified collateralised lending pool.
/// @notice Single-asset pool with an interest index, owner-set LTV and a
///         liquidation path. Demonstrates owner-controlled risk parameters and a
///         privileged reserve sweep.
contract LendingPool is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable asset;

    uint256 public borrowIndex = 1e18;
    uint256 public lastAccrual;
    uint256 public baseRateBps = 200; // 2% per accrual period
    uint256 public collateralFactorBps = 7500; // 75% LTV
    uint256 public liquidationBonusBps = 500;

    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debtPrincipal;
    mapping(address => bool) public liquidator;

    event Deposited(address indexed account, uint256 amount);
    event Borrowed(address indexed account, uint256 amount);
    event Repaid(address indexed account, uint256 amount);
    event Liquidated(address indexed account, address indexed liquidator, uint256 repaid);
    event ParamsUpdated(uint256 baseRateBps, uint256 collateralFactorBps);

    constructor(address _asset) Ownable(msg.sender) {
        asset = IERC20(_asset);
        lastAccrual = block.timestamp;
    }

    modifier accrue() {
        uint256 periods = (block.timestamp - lastAccrual) / 1 days;
        if (periods > 0) {
            borrowIndex += (borrowIndex * baseRateBps * periods) / 10_000;
            lastAccrual = block.timestamp;
        }
        _;
    }

    function setParams(uint256 _baseRateBps, uint256 _collateralFactorBps) external onlyOwner {
        require(_collateralFactorBps <= 9000, "LendingPool: LTV too high");
        baseRateBps = _baseRateBps;
        collateralFactorBps = _collateralFactorBps;
        emit ParamsUpdated(_baseRateBps, _collateralFactorBps);
    }

    function setLiquidator(address account, bool allowed) external onlyOwner {
        liquidator[account] = allowed;
    }

    function debtOf(address account) public view returns (uint256) {
        return (debtPrincipal[account] * borrowIndex) / 1e18;
    }

    function isHealthy(address account) public view returns (bool) {
        uint256 limit = (collateral[account] * collateralFactorBps) / 10_000;
        return debtOf(account) <= limit;
    }

    function deposit(uint256 amount) external nonReentrant accrue {
        asset.safeTransferFrom(msg.sender, address(this), amount);
        collateral[msg.sender] += amount;
        emit Deposited(msg.sender, amount);
    }

    function borrow(uint256 amount) external nonReentrant accrue {
        debtPrincipal[msg.sender] += (amount * 1e18) / borrowIndex;
        require(isHealthy(msg.sender), "LendingPool: unhealthy");
        asset.safeTransfer(msg.sender, amount);
        emit Borrowed(msg.sender, amount);
    }

    function repay(uint256 amount) external nonReentrant accrue {
        uint256 debt = debtOf(msg.sender);
        uint256 pay = amount > debt ? debt : amount;
        debtPrincipal[msg.sender] -= (pay * 1e18) / borrowIndex;
        asset.safeTransferFrom(msg.sender, address(this), pay);
        emit Repaid(msg.sender, pay);
    }

    function withdrawCollateral(uint256 amount) external nonReentrant accrue {
        collateral[msg.sender] -= amount;
        require(isHealthy(msg.sender), "LendingPool: would be unhealthy");
        asset.safeTransfer(msg.sender, amount);
    }

    function liquidate(address account) external nonReentrant accrue {
        require(liquidator[msg.sender] || msg.sender == owner(), "LendingPool: not liquidator");
        require(!isHealthy(account), "LendingPool: healthy");
        uint256 debt = debtOf(account);
        uint256 seize = debt + (debt * liquidationBonusBps) / 10_000;
        if (seize > collateral[account]) seize = collateral[account];
        collateral[account] -= seize;
        debtPrincipal[account] = 0;
        asset.safeTransfer(msg.sender, seize);
        emit Liquidated(account, msg.sender, debt);
    }

    /// @notice Owner can sweep accumulated interest / surplus. High-trust.
    function sweepSurplus(address to, uint256 amount) external onlyOwner {
        asset.safeTransfer(to, amount);
    }
}
