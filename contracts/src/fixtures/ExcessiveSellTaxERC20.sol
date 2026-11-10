// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 4 - Token with an excessive (90%) sell tax and no buy tax.
contract ExcessiveSellTaxERC20 is ERC20, Ownable {
    address public pair;
    address public feeRecipient;

    constructor() ERC20("Excessive Sell Tax Token", "ESTAX") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
        feeRecipient = msg.sender;
    }

    function setPair(address _pair) external onlyOwner {
        pair = _pair;
    }

    function _update(address from, address to, uint256 value) internal override {
        uint256 fee;
        if (to == pair && pair != address(0) && from != address(0)) {
            fee = (value * 9000) / 10_000;
            super._update(from, feeRecipient, fee);
        }
        super._update(from, to, value - fee);
    }
}
