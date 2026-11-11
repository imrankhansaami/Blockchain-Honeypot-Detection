// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20FlashMint} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20FlashMint.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title ERC-3156 flash-mintable ERC-20.
/// @notice Mints tokens for the duration of a flash loan. Tests the analyzer's
///         handling of EIP-3156 lenders and supply that changes within a tx.
contract FlashMintToken is ERC20, ERC20FlashMint, Ownable {
    uint256 public constant FEE_BPS = 0;

    constructor() ERC20("Flash Mint Token", "FLSH") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function flashFee(address, uint256 amount) public view override returns (uint256) {
        return (amount * FEE_BPS) / 10_000;
    }

    function _flashFee(address, uint256 amount) internal view override returns (uint256) {
        return (amount * FEE_BPS) / 10_000;
    }
}
