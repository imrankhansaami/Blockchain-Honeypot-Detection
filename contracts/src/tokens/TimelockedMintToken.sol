// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 22 - Token whose owner is an external contract (e.g. a
///        TimelockController or MultiSigWallet).
/// @notice Demonstrates the correct mitigation for owner-privilege risk: the
///         privileged account is a contract with its own controls, not a hot key.
contract TimelockedMintToken is ERC20, Ownable {
    uint256 public immutable cap;

    constructor(address initialOwner, uint256 _cap)
        ERC20("Timelocked Mint Token", "TLM")
        Ownable(initialOwner)
    {
        cap = _cap;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= cap, "TimelockedMintToken: cap exceeded");
        _mint(to, amount);
    }
}
