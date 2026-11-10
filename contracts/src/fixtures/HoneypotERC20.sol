// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 2 - Honeypot: buys are allowed, ordinary sells revert.
/// @notice Non-owner, non-whitelisted accounts can receive tokens (buy) but
///         cannot send them to the DEX pair (sell).
contract HoneypotERC20 is ERC20, Ownable {
    address public pair;
    bool public tradingEnabled;
    mapping(address => bool) public isWhitelisted;

    event PairSet(address pair);

    constructor() ERC20("Honeypot Token", "HNY") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
        isWhitelisted[msg.sender] = true;
    }

    function setPair(address _pair) external onlyOwner {
        pair = _pair;
        emit PairSet(_pair);
    }

    function setWhitelisted(address account, bool value) external onlyOwner {
        isWhitelisted[account] = value;
    }

    function enableTrading() external onlyOwner {
        tradingEnabled = true;
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            require(tradingEnabled, "Trading not enabled");
            if (to == pair && from != owner() && !isWhitelisted[from]) {
                revert("Sell not allowed");
            }
        }
        super._update(from, to, value);
    }
}
