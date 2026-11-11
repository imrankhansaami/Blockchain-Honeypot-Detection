// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Dividend-paying ERC-20.
/// @notice Distributes an ERC-20 dividend stream proportionate to holdings using
///         a magnified-dividend-per-share accumulator. A classic "reflection of
///         profit" design, and a genuine incentive mechanism.
contract DividendToken is ERC20, Ownable {
    using SafeERC20 for IERC20;

    uint256 public constant MAGNITUDE = 2 ** 128;

    IERC20 public immutable dividendToken;

    uint256 public magnifiedDividendPerShare;
    uint256 public totalDividendsDistributed;

    mapping(address => int256) public magnifiedDividendCorrections;
    mapping(address => uint256) public withdrawnDividends;

    event DividendsDistributed(address indexed by, uint256 amount);
    event DividendWithdrawn(address indexed to, uint256 amount);

    constructor(address _dividendToken) ERC20("Dividend Token", "DVD") Ownable(msg.sender) {
        dividendToken = IERC20(_dividendToken);
        _mint(msg.sender, 1_000_000 ether);
    }

    /// @notice Owner funds a dividend round; it is distributed pro-rata.
    function distributeDividends(uint256 amount) external onlyOwner {
        require(totalSupply() > 0, "DividendToken: no supply");
        dividendToken.safeTransferFrom(msg.sender, address(this), amount);
        magnifiedDividendPerShare += (amount * MAGNITUDE) / totalSupply();
        totalDividendsDistributed += amount;
        emit DividendsDistributed(msg.sender, amount);
    }

    function accumulativeDividendOf(address account) public view returns (uint256) {
        return uint256(int256(magnifiedDividendPerShare * balanceOf(account)) + magnifiedDividendCorrections[account])
            / MAGNITUDE;
    }

    function withdrawableDividendOf(address account) public view returns (uint256) {
        return accumulativeDividendOf(account) - withdrawnDividends[account];
    }

    function withdrawDividend() external {
        uint256 due = withdrawableDividendOf(msg.sender);
        require(due > 0, "DividendToken: nothing to withdraw");
        withdrawnDividends[msg.sender] += due;
        dividendToken.safeTransfer(msg.sender, due);
        emit DividendWithdrawn(msg.sender, due);
    }

    function _update(address from, address to, uint256 value) internal override {
        super._update(from, to, value);
        int256 magnitude = int256(magnifiedDividendPerShare);
        if (from != address(0)) {
            magnifiedDividendCorrections[from] += magnitude * int256(value);
        }
        if (to != address(0)) {
            magnifiedDividendCorrections[to] -= magnitude * int256(value);
        }
    }
}
