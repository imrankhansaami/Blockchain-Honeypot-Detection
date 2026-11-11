// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Fixture 20 - ERC-20 with EIP-2612 permit and a capped, role-gated mint.
/// @notice A comparatively well-behaved token: minting is capped and restricted
///         to a role, used as a negative control for over-flagging.
contract PermitToken is ERC20, ERC20Permit, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    uint256 public immutable mintCap;

    constructor(uint256 initialSupply, uint256 _mintCap)
        ERC20("Permit Token", "PRMT")
        ERC20Permit("Permit Token")
    {
        require(initialSupply <= _mintCap, "PermitToken: initial exceeds cap");
        mintCap = _mintCap;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _mint(msg.sender, initialSupply);
    }

    /// @notice Mint up to the immutable cap. No owner can exceed it.
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(totalSupply() + amount <= mintCap, "PermitToken: cap exceeded");
        _mint(to, amount);
    }
}
