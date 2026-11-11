// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title ERC-4626 yield vault with owner-managed strategy assets.
/// @notice `totalAssets` tracks real token balance, so the share price only rises
///         when the owner harvests strategy proceeds. A useful control case for
///         "owner can change share price" analysis.
contract YieldVault is ERC4626, Ownable {
    event Harvested(address indexed by, uint256 amount);

    constructor(IERC20 asset_)
        ERC4626(asset_)
        ERC20("Yield Vault Share", "YVS")
        Ownable(msg.sender)
    {}

    function totalAssets() public view override returns (uint256) {
        return IERC20(asset()).balanceOf(address(this));
    }

    /// @notice Move realised strategy profit into the vault, increasing share value.
    function harvest(uint256 amount) external onlyOwner {
        IERC20(asset()).transferFrom(msg.sender, address(this), amount);
        emit Harvested(msg.sender, amount);
    }
}
