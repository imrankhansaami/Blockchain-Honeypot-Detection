// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title Fixture 19 - Bonding-curve token.
/// @notice Price rises linearly with supply; anyone can buy and sell against the
///         contract for native currency. The owner controls the curve parameters,
///         which is a powerful economic privilege.
contract BondingCurveToken is ERC20, Ownable, ReentrancyGuard {
    uint256 public basePrice; // wei per whole token at zero supply
    uint256 public slope; // wei added per whole token of supply

    event CurveUpdated(uint256 basePrice, uint256 slope);
    event Bought(address indexed buyer, uint256 amount, uint256 cost);
    event Sold(address indexed seller, uint256 amount, uint256 refund);

    constructor(uint256 _basePrice, uint256 _slope) ERC20("Bonding Curve Token", "BOND") Ownable(msg.sender) {
        basePrice = _basePrice;
        slope = _slope;
    }

    receive() external payable {}

    /// @notice Current marginal price in wei per whole token.
    function price() public view returns (uint256) {
        return basePrice + (slope * totalSupply()) / 1e18;
    }

    function quoteBuy(uint256 amount) public view returns (uint256) {
        uint256 start = totalSupply();
        uint256 avg = basePrice + (slope * (start + amount / 2)) / 1e18;
        return (avg * amount) / 1e18;
    }

    function buy() external payable nonReentrant returns (uint256 amount) {
        amount = (msg.value * 1e18) / price();
        require(amount > 0, "BondingCurveToken: amount too small");
        _mint(msg.sender, amount);
        emit Bought(msg.sender, amount, msg.value);
    }

    function sell(uint256 amount) external nonReentrant returns (uint256 refund) {
        uint256 supply = totalSupply();
        uint256 avg = basePrice + (slope * (supply - amount / 2)) / 1e18;
        refund = (avg * amount) / 1e18;
        _burn(msg.sender, amount);
        (bool ok,) = msg.sender.call{value: refund}("");
        require(ok, "BondingCurveToken: refund failed");
        emit Sold(msg.sender, amount, refund);
    }

    function setCurve(uint256 _basePrice, uint256 _slope) external onlyOwner {
        basePrice = _basePrice;
        slope = _slope;
        emit CurveUpdated(_basePrice, _slope);
    }
}
