// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title Fixture 1 - Standard ERC-20 token with no owner privileges or restrictions.
contract StandardERC20 is ERC20 {
    constructor() ERC20("Standard Token", "STD") {
        _mint(msg.sender, 1_000_000 ether);
    }
}
