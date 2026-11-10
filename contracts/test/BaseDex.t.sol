// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {MockWETH} from "../src/mocks/MockWETH.sol";
import {MockUniswapV2Factory} from "../src/mocks/MockUniswapV2Factory.sol";
import {MockUniswapV2Router02} from "../src/mocks/MockUniswapV2Router02.sol";

/// @title Shared DEX + trader harness for fixture tests.
abstract contract BaseDex is Test {
    MockWETH internal weth;
    MockUniswapV2Factory internal factory;
    MockUniswapV2Router02 internal router;

    address internal trader = address(0xA11CE);
    address internal owner;

    function _deployDex() internal {
        weth = new MockWETH();
        factory = new MockUniswapV2Factory();
        router = new MockUniswapV2Router02(address(factory), address(weth));
        owner = address(this);
        vm.deal(trader, 1_000 ether);
        vm.deal(owner, 1_000 ether);
    }

    /// @dev Add ETH liquidity for a token held by this test contract.
    function _addLiquidityETH(address token, uint256 tokenAmount, uint256 ethAmount)
        internal
        returns (address pair)
    {
        IERC20(token).approve(address(router), tokenAmount);
        router.addLiquidityETH{value: ethAmount}(token, tokenAmount, 0, 0, address(this), block.timestamp);
        pair = factory.getPair(token, address(weth));
    }

    /// @dev Buy tokens with ETH as the trader; returns the token amount received.
    /// @notice Uses the fee-on-transfer-supporting variant, which is what a
    ///         honeypot detector must use to remain robust to taxed tokens.
    function _buy(address token, uint256 ethIn) internal returns (uint256 received) {
        address[] memory path = new address[](2);
        path[0] = address(weth);
        path[1] = token;
        uint256 before = IERC20(token).balanceOf(trader);
        vm.prank(trader);
        router.swapExactETHForTokensSupportingFeeOnTransferTokens{value: ethIn}(0, path, trader, block.timestamp);
        received = IERC20(token).balanceOf(trader) - before;
    }

    /// @dev Attempt to sell tokens as the trader; returns ETH received.
    function _sell(address token, uint256 tokenIn) internal returns (uint256 ethReceived) {
        address[] memory path = new address[](2);
        path[0] = token;
        path[1] = address(weth);
        vm.startPrank(trader);
        IERC20(token).approve(address(router), tokenIn);
        uint256 before = trader.balance;
        router.swapExactTokensForETHSupportingFeeOnTransferTokens(tokenIn, 0, path, trader, block.timestamp);
        ethReceived = trader.balance - before;
        vm.stopPrank();
    }

    receive() external payable {}
}
