// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 23 - Token whose fees can be redirected by the owner.
/// @notice Fees accrue to a configurable recipient. A sudden recipient change is
///         a classic "fee redirect" rug vector the analyzer should surface.
contract FeeRedirectToken is ERC20, Ownable {
    address public pair;
    address public feeRecipient;
    uint256 public buyFeeBps = 300;
    uint256 public sellFeeBps = 500;

    event FeeRecipientUpdated(address indexed recipient);
    event FeesUpdated(uint256 buyFeeBps, uint256 sellFeeBps);

    constructor(address initialRecipient) ERC20("Fee Redirect Token", "FRD") Ownable(msg.sender) {
        feeRecipient = initialRecipient;
        _mint(msg.sender, 1_000_000 ether);
    }

    function setPair(address _pair) external onlyOwner {
        pair = _pair;
    }

    function setFeeRecipient(address recipient) external onlyOwner {
        require(recipient != address(0), "FeeRedirectToken: zero recipient");
        feeRecipient = recipient;
        emit FeeRecipientUpdated(recipient);
    }

    function setFees(uint256 _buyFeeBps, uint256 _sellFeeBps) external onlyOwner {
        require(_buyFeeBps <= 3000 && _sellFeeBps <= 3000, "FeeRedirectToken: fee too high");
        buyFeeBps = _buyFeeBps;
        sellFeeBps = _sellFeeBps;
        emit FeesUpdated(_buyFeeBps, _sellFeeBps);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (pair != address(0) && from != address(0) && to != address(0)) {
            uint256 bps;
            if (from == pair) bps = buyFeeBps;
            else if (to == pair) bps = sellFeeBps;
            if (bps > 0) {
                uint256 fee = (value * bps) / 10_000;
                super._update(from, feeRecipient, fee);
                super._update(from, to, value - fee);
                return;
            }
        }
        super._update(from, to, value);
    }
}
