// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Soulbound (non-transferable) ERC-20.
/// @notice Tokens can only be minted or burned; any peer-to-peer transfer reverts.
///         Tests the analyzer's handling of intentionally non-transferable tokens
///         so they are not mislabelled as honeypots.
contract SoulboundToken is ERC20, Ownable {
    constructor() ERC20("Soulbound Token", "SBT") Ownable(msg.sender) {}

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external onlyOwner {
        _burn(from, amount);
    }

    /// @dev Only mint (from == 0) and burn (to == 0) are permitted.
    function _update(address from, address to, uint256 value) internal override {
        require(from == address(0) || to == address(0), "SoulboundToken: non-transferable");
        super._update(from, to, value);
    }
}
