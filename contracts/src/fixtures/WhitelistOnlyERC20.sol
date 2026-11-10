// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 6 - Token where transfers only work for whitelisted accounts.
contract WhitelistOnlyERC20 is ERC20, Ownable {
    mapping(address => bool) public isWhitelisted;

    event Whitelisted(address indexed account, bool value);

    constructor() ERC20("Whitelist Token", "WLST") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
        isWhitelisted[msg.sender] = true;
    }

    function setWhitelisted(address account, bool value) external onlyOwner {
        isWhitelisted[account] = value;
        emit Whitelisted(account, value);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            require(isWhitelisted[from] || isWhitelisted[to], "Not whitelisted");
        }
        super._update(from, to, value);
    }
}
