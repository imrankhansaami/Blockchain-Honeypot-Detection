// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IUniswapV2Factory} from "../interfaces/IUniswapV2Factory.sol";
import {IUniswapV2Pair} from "../interfaces/IUniswapV2Pair.sol";

/// @title On-chain pool inspector.
/// @notice Read-only helper the analyzer calls to obtain pair reserves, spot
///         price and a liquidity-depth estimate without trusting off-chain data.
contract PoolInspector {
    struct PoolReport {
        address pair;
        address token0;
        address token1;
        uint112 reserve0;
        uint112 reserve1;
        uint256 priceToken1PerToken0; // scaled 1e18
        uint256 k; // constant-product invariant
        bool exists;
    }

    /// @notice Inspect the pair between `token` and `quote` on `factory`.
    function inspect(address factory, address token, address quote) external view returns (PoolReport memory report) {
        address pair = IUniswapV2Factory(factory).getPair(token, quote);
        if (pair == address(0)) {
            return report; // exists = false
        }
        report.pair = pair;
        report.exists = true;
        report.token0 = IUniswapV2Pair(pair).token0();
        report.token1 = IUniswapV2Pair(pair).token1();
        (uint112 r0, uint112 r1,) = IUniswapV2Pair(pair).getReserves();
        report.reserve0 = r0;
        report.reserve1 = r1;
        report.k = uint256(r0) * r1;
        if (r0 > 0) {
            report.priceToken1PerToken0 = (uint256(r1) * 1e18) / r0;
        }
    }

    /// @notice True when a pair exists and both reserves are non-zero.
    function hasLiquidity(address factory, address token, address quote) external view returns (bool) {
        address pair = IUniswapV2Factory(factory).getPair(token, quote);
        if (pair == address(0)) return false;
        (uint112 r0, uint112 r1,) = IUniswapV2Pair(pair).getReserves();
        return r0 > 0 && r1 > 0;
    }

    /// @notice Approximate token price in native units for a simple spot quote.
    function spotPrice(address factory, address token, address quote, bool tokenIsToken0)
        external
        view
        returns (uint256 priceQuotePerToken)
    {
        address pair = IUniswapV2Factory(factory).getPair(token, quote);
        require(pair != address(0), "PoolInspector: no pair");
        (uint112 r0, uint112 r1,) = IUniswapV2Pair(pair).getReserves();
        (uint256 tokenReserve, uint256 quoteReserve) = tokenIsToken0 ? (uint256(r0), uint256(r1)) : (uint256(r1), uint256(r0));
        require(tokenReserve > 0, "PoolInspector: no liquidity");
        priceQuotePerToken = (quoteReserve * 1e18) / tokenReserve;
    }
}
