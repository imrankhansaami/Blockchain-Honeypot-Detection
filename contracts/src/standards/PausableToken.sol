// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Pausable} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Pausable.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Pausable ERC-20 with a role-style pause.
/// @notice Reference for the "pausable transfer" privilege: the owner can halt
///         every transfer. Legitimate in some designs, a freeze risk in others.
contract PausableToken is ERC20, ERC20Pausable, Ownable {
    constructor() ERC20("Pausable Token", "PAUS") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Pausable) {
        super._update(from, to, value);
    }
}
