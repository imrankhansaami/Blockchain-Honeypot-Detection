// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 8 - Token with an owner-controlled global trading switch.
contract TradingSwitchERC20 is ERC20, Ownable {
    bool public tradingEnabled;

    event TradingToggled(bool enabled);

    constructor() ERC20("Trading Switch Token", "TSW") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function enableTrading() external onlyOwner {
        tradingEnabled = true;
        emit TradingToggled(true);
    }

    function disableTrading() external onlyOwner {
        tradingEnabled = false;
        emit TradingToggled(false);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            require(tradingEnabled, "Trading disabled");
        }
        super._update(from, to, value);
    }
}
