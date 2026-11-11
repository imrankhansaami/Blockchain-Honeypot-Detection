// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 24 - Token with an obscured minting path.
/// @notice There is no `mint` selector: supply inflation happens inside
///         `syncLiquidity`, which looks like an ordinary fee-processing call.
///         Tests the analyzer's ability to find hidden mint logic in source.
contract HiddenMintToken is ERC20, Ownable {
    uint256 public constant MINT_CAP = 10_000_000 ether;

    constructor() ERC20("Hidden Mint Token", "HIDN") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    /// @notice Innocuous-looking name; actually mints to the caller's treasury.
    function syncLiquidity(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MINT_CAP, "HiddenMintToken: cap");
        _mint(to, amount);
    }

    /// @notice Another alias.
    function processFees(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MINT_CAP, "HiddenMintToken: cap");
        _mint(to, amount);
    }
}
