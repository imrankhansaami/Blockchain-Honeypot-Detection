// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 3 - Token with owner-adjustable buy and sell taxes.
contract AdjustableTaxERC20 is ERC20, Ownable {
    address public pair;
    address public feeRecipient;
    uint256 public buyTaxBps;
    uint256 public sellTaxBps;

    event TaxesUpdated(uint256 buyTaxBps, uint256 sellTaxBps);

    constructor() ERC20("Adjustable Tax Token", "ATAX") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
        feeRecipient = msg.sender;
    }

    function setPair(address _pair) external onlyOwner {
        pair = _pair;
    }

    function setFeeRecipient(address recipient) external onlyOwner {
        feeRecipient = recipient;
    }

    function setTaxes(uint256 _buyTaxBps, uint256 _sellTaxBps) external onlyOwner {
        require(_buyTaxBps <= 2500 && _sellTaxBps <= 2500, "Tax too high");
        buyTaxBps = _buyTaxBps;
        sellTaxBps = _sellTaxBps;
        emit TaxesUpdated(_buyTaxBps, _sellTaxBps);
    }

    function _update(address from, address to, uint256 value) internal override {
        uint256 fee;
        if (pair != address(0) && (from == pair || to == pair) && from != address(0) && to != address(0)) {
            uint256 bps = from == pair ? buyTaxBps : sellTaxBps;
            fee = (value * bps) / 10_000;
            if (fee > 0) {
                super._update(from, feeRecipient, fee);
            }
        }
        super._update(from, to, value - fee);
    }
}
