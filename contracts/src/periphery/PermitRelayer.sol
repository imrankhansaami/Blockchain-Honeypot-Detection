// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Permit.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @title Gasless permit relayer.
/// @notice Lets a third party submit an EIP-2612 permit and an immediate
///         transfer, so a user can pay with a signature instead of a transaction.
contract PermitRelayer {
    using SafeERC20 for IERC20;

    event Relayed(address indexed token, address indexed owner, address indexed to, uint256 value, address relayer);

    /// @notice Apply `owner`'s signature, then move `value` from owner to `to`.
    function relay(
        address token,
        address owner,
        address to,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        IERC20Permit(token).permit(owner, address(this), value, deadline, v, r, s);
        IERC20(token).safeTransferFrom(owner, to, value);
        emit Relayed(token, owner, to, value, msg.sender);
    }
}
