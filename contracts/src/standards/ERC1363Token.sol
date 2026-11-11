// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC1363} from "@openzeppelin/contracts/token/ERC20/extensions/ERC1363.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title ERC-1363 transfer-and-call token.
/// @notice Notifies a recipient contract in the same transaction as a transfer.
///         Tests handling of callback-based tokens, a common reentrancy surface.
contract ERC1363Token is ERC1363, Ownable {
    constructor() ERC20("ERC1363 Token", "E1363") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }
}
