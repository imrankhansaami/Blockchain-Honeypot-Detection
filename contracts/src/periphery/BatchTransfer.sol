// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @title Batch ERC-20 transfer helpers.
/// @notice Convenience for airdrops and treasury operations; also a common way
///         for a compromised key to drain many recipients in one transaction.
contract BatchTransfer {
    using SafeERC20 for IERC20;

    event BatchSent(address indexed token, address indexed from, uint256 total, uint256 count);

    /// @notice Transfer `amount` of `token` to every address in `recipients`.
    function batchEqual(IERC20 token, address[] calldata recipients, uint256 amount) external {
        uint256 total = amount * recipients.length;
        token.safeTransferFrom(msg.sender, address(this), total);
        for (uint256 i; i < recipients.length; i++) {
            token.safeTransfer(recipients[i], amount);
        }
        emit BatchSent(address(token), msg.sender, total, recipients.length);
    }

    /// @notice Transfer per-recipient amounts. Lengths must match.
    function batchAmounts(IERC20 token, address[] calldata recipients, uint256[] calldata amounts) external {
        require(recipients.length == amounts.length, "BatchTransfer: length mismatch");
        uint256 total;
        for (uint256 i; i < recipients.length; i++) {
            token.safeTransferFrom(msg.sender, recipients[i], amounts[i]);
            total += amounts[i];
        }
        emit BatchSent(address(token), msg.sender, total, recipients.length);
    }
}
