// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {ERC20Votes} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import {Nonces} from "@openzeppelin/contracts/utils/Nonces.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Fixture 21 - Governance token with votes and a capped mint.
/// @notice Combines ERC20Permit, ERC20Votes (delegation, checkpoints) and
///         AccessControl. Used to exercise role detection and vote-tracking
///         analysis paths.
contract GovernanceToken is ERC20, ERC20Permit, ERC20Votes, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    uint256 public immutable cap;
    bool public transfersPaused;

    event TransfersPausedSet(bool paused);

    constructor(uint256 initialSupply, uint256 _cap)
        ERC20("Governance Token", "GOV")
        ERC20Permit("Governance Token")
    {
        require(initialSupply <= _cap, "GovernanceToken: initial exceeds cap");
        cap = _cap;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        _mint(msg.sender, initialSupply);
    }

    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(totalSupply() + amount <= cap, "GovernanceToken: cap exceeded");
        _mint(to, amount);
    }

    function setTransfersPaused(bool paused) external onlyRole(PAUSER_ROLE) {
        transfersPaused = paused;
        emit TransfersPausedSet(paused);
    }

    function _update(address from, address to, uint256 value)
        internal
        override(ERC20, ERC20Votes)
    {
        if (from != address(0) && to != address(0)) {
            require(!transfersPaused, "GovernanceToken: paused");
        }
        super._update(from, to, value);
    }

    function nonces(address owner) public view override(ERC20Permit, Nonces) returns (uint256) {
        return super.nonces(owner);
    }
}
