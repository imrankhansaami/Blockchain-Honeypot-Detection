// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IUniswapV2PairMinimal {
    function transfer(address, uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

/// @title Fixture 26 - Token that can pull its own liquidity.
/// @notice The contract holds LP tokens and the owner can redeem them at any
///         time, removing all liquidity from the pool. A severe rug vector.
contract LiquidityPullToken is ERC20, Ownable {
    IUniswapV2PairMinimal public pair;
    bool public liquidityLocked;

    event PairSet(address indexed pair);
    event LiquidityPulled(uint256 amount);

    constructor() ERC20("Liquidity Pull Token", "LPT") Ownable(msg.sender) {
        _mint(msg.sender, 1_000_000 ether);
    }

    function setPair(address _pair) external onlyOwner {
        pair = IUniswapV2PairMinimal(_pair);
        emit PairSet(_pair);
    }

    function lockLiquidity() external onlyOwner {
        liquidityLocked = true;
    }

    /// @notice Owner redeems the LP tokens held by the contract.
    function pullLiquidity() external onlyOwner {
        require(!liquidityLocked, "LiquidityPullToken: locked");
        uint256 balance = pair.balanceOf(address(this));
        require(balance > 0, "LiquidityPullToken: no liquidity");
        require(pair.transfer(owner(), balance), "LiquidityPullToken: transfer failed");
        emit LiquidityPulled(balance);
    }
}
