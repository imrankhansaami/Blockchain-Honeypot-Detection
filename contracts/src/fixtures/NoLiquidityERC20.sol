// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title Fixture 13 - Ordinary token intentionally left without any liquidity pair.
/// @dev Same code as StandardERC20 but used by tests that must verify the
///      "insufficient liquidity" path of the simulation engine.
contract NoLiquidityERC20 is ERC20 {
    constructor() ERC20("No Liquidity Token", "NOLIQ") {
        _mint(msg.sender, 1_000_000 ether);
    }
}
