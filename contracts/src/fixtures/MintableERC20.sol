// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 9 - Token with unrestricted owner minting.
contract MintableERC20 is ERC20, Ownable {
    constructor() ERC20("Mintable Token", "MINT") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    /// @notice Arbitrary minting with no cap and no reason.
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
