// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 5 - Token with an owner-controlled blacklist.
contract BlacklistERC20 is ERC20, Ownable {
    mapping(address => bool) public isBlacklisted;

    event Blacklisted(address indexed account, bool value);

    constructor() ERC20("Blacklist Token", "BLK") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function addBlacklist(address account) external onlyOwner {
        isBlacklisted[account] = true;
        emit Blacklisted(account, true);
    }

    function removeBlacklist(address account) external onlyOwner {
        isBlacklisted[account] = false;
        emit Blacklisted(account, false);
    }

    function _update(address from, address to, uint256 value) internal override {
        require(!isBlacklisted[from] && !isBlacklisted[to], "Blacklisted");
        super._update(from, to, value);
    }
}
