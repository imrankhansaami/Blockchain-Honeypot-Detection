// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Rewards distributor.
/// @notice Owner uploads a set of beneficiaries with weights and distributes a
///         deposited reward proportionally. A stand-in for merkle distributors.
contract RewardsDistributor is Ownable {
    using SafeERC20 for IERC20;

    struct Share {
        address account;
        uint256 weight;
    }

    Share[] private _shares;
    uint256 private _totalWeight;

    event SharesSet(uint256 count, uint256 totalWeight);
    event Distributed(address indexed token, uint256 amount, uint256 recipients);

    constructor(address initialOwner) Ownable(initialOwner) {}

    function shares() external view returns (Share[] memory) {
        return _shares;
    }

    function totalWeight() external view returns (uint256) {
        return _totalWeight;
    }

    function setShares(Share[] calldata list) external onlyOwner {
        delete _shares;
        uint256 total;
        for (uint256 i; i < list.length; i++) {
            require(list[i].account != address(0), "RewardsDistributor: zero account");
            require(list[i].weight > 0, "RewardsDistributor: zero weight");
            total += list[i].weight;
            _shares.push(list[i]);
        }
        _totalWeight = total;
        emit SharesSet(list.length, total);
    }

    /// @notice Distribute the contract's balance of `token` proportionally.
    function distribute(IERC20 token) external returns (uint256 distributed) {
        uint256 balance = token.balanceOf(address(this));
        require(balance > 0 && _totalWeight > 0, "RewardsDistributor: nothing to distribute");
        for (uint256 i; i < _shares.length; i++) {
            uint256 amount = (balance * _shares[i].weight) / _totalWeight;
            if (amount > 0) {
                token.safeTransfer(_shares[i].account, amount);
                distributed += amount;
            }
        }
        emit Distributed(address(token), distributed, _shares.length);
    }
}
