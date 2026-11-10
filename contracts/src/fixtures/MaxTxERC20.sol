// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 7 - Token with owner-controlled max transaction / max wallet limits.
contract MaxTxERC20 is ERC20, Ownable {
    uint256 public maxTxAmount;
    uint256 public maxWalletAmount;

    constructor() ERC20("Max Tx Token", "MAXTX") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
        maxTxAmount = 10_000 ether;
        maxWalletAmount = 20_000 ether;
    }

    function setMaxTxAmount(uint256 amount) external onlyOwner {
        maxTxAmount = amount;
    }

    function setMaxWalletAmount(uint256 amount) external onlyOwner {
        maxWalletAmount = amount;
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            require(value <= maxTxAmount, "Max tx exceeded");
            if (to != address(this)) {
                require(balanceOf(to) + value <= maxWalletAmount, "Max wallet exceeded");
            }
        }
        super._update(from, to, value);
    }
}
