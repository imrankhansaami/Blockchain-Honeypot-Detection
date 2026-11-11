// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Burnable} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import {ERC20Capped} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Capped.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Capped, burnable ERC-20 (a well-behaved control).
/// @notice Supply can never exceed the immutable cap and any holder may burn.
///         Used as a negative control for supply-manipulation findings.
contract CappedBurnableToken is ERC20, ERC20Burnable, ERC20Capped, Ownable {
    constructor(uint256 cap_) ERC20("Capped Burnable Token", "CAPB") ERC20Capped(cap_) Ownable(msg.sender) {
        _mint(msg.sender, cap_);
    }

    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Capped) {
        super._update(from, to, value);
    }
}
