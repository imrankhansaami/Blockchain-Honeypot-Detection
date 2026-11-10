// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title Fixture 11 - Fee-on-transfer token (5% deducted on every transfer).
contract FeeOnTransferERC20 is ERC20 {
    address public feeRecipient;
    uint256 public constant FEE_BPS = 500;

    constructor() ERC20("Fee On Transfer Token", "FOT") {
        _mint(msg.sender, 1_000_000 ether);
        feeRecipient = msg.sender;
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            uint256 fee = (value * FEE_BPS) / 10_000;
            if (fee > 0) {
                super._update(from, feeRecipient, fee);
            }
            super._update(from, to, value - fee);
        } else {
            super._update(from, to, value);
        }
    }
}
