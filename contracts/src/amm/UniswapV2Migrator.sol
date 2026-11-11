// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IUniswapV2Router02} from "../interfaces/IUniswapV2Router02.sol";
import {TransferHelper} from "./libraries/TransferHelper.sol";

/// @title Uniswap V2 liquidity migrator (reference).
/// @notice Withdraws liquidity from a token/ETH pair and re-deposits it, moving
///         liquidity between pools. Relevant to the analyzer because liquidity
///         movement is central to rug detection.
contract UniswapV2Migrator {
    using SafeERC20 for IERC20;

    IUniswapV2Router02 public immutable router;

    event Migrated(address indexed token, uint256 liquidity, uint256 amountToken, uint256 amountETH);

    constructor(address _router) {
        router = IUniswapV2Router02(_router);
    }

    /// @notice Migrate the caller's LP tokens for `token`/WETH into a fresh position.
    function migrate(address token, uint256 liquidity, uint256 amountTokenMin, uint256 amountETHMin, uint256 deadline)
        external
        returns (uint256 amountToken, uint256 amountETH)
    {
        address pair = _pairFor(token);
        TransferHelper.safeTransferFrom(token, pair, address(this), liquidity);

        uint256 tokenBalanceBefore = IERC20(token).balanceOf(address(this));
        (uint256 removedToken, uint256 removedEth) =
            router.removeLiquidityETH(token, liquidity, amountTokenMin, amountETHMin, address(this), deadline);
        require(
            IERC20(token).balanceOf(address(this)) == tokenBalanceBefore + removedToken,
            "UniswapV2Migrator: token accounting"
        );

        IERC20(token).forceApprove(address(router), removedToken);
        (amountToken, amountETH,) =
            router.addLiquidityETH{value: removedEth}(token, removedToken, 0, 0, msg.sender, deadline);

        uint256 tokenRefund = removedToken - amountToken;
        if (tokenRefund > 0) {
            IERC20(token).safeTransfer(msg.sender, tokenRefund);
        }
        if (address(this).balance > 0) {
            TransferHelper.safeTransferETH(msg.sender, address(this).balance);
        }
        emit Migrated(token, liquidity, amountToken, amountETH);
    }

    function _pairFor(address token) private view returns (address) {
        address weth = router.WETH();
        (address token0, address token1) = token < weth ? (token, weth) : (weth, token);
        address factory = router.factory();
        (bool ok, bytes memory data) =
            factory.staticcall(abi.encodeWithSignature("getPair(address,address)", token0, token1));
        require(ok, "UniswapV2Migrator: getPair failed");
        address pair = abi.decode(data, (address));
        require(pair != address(0), "UniswapV2Migrator: no pair");
        return pair;
    }

    receive() external payable {}
}
