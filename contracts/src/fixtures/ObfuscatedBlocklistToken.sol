// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 27 - Obfuscated blocklist token.
/// @notice Uses an innocuous mapping name (`_flags`) and a generic modifier to
///         block accounts, so name-based detection alone would miss it. The
///         analyzer must reason about the transfer condition, not the wording.
contract ObfuscatedBlocklistToken is ERC20, Ownable {
    mapping(address => uint256) private _flags;
    uint256 private constant FLAG_BLOCKED = 1;

    event FlagUpdated(address indexed account, uint256 flag);

    constructor() ERC20("Obfuscated Blocklist Token", "OBF") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function setFlag(address account, uint256 flag) external onlyOwner {
        _flags[account] = flag;
        emit FlagUpdated(account, flag);
    }

    function isBlocked(address account) external view returns (bool) {
        return _flags[account] & FLAG_BLOCKED != 0;
    }

    modifier gate(address from, address to) {
        require(_flags[from] & FLAG_BLOCKED == 0 && _flags[to] & FLAG_BLOCKED == 0, "OBF: account restricted");
        _;
    }

    function transfer(address to, uint256 value) public override gate(msg.sender, to) returns (bool) {
        return super.transfer(to, value);
    }

    function transferFrom(address from, address to, uint256 value)
        public
        override
        gate(from, to)
        returns (bool)
    {
        return super.transferFrom(from, to, value);
    }
}
