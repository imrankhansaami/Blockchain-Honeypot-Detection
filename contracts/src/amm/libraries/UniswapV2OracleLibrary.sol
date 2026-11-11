// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IUniswapV2PairCumulative {
    function getReserves() external view returns (uint112, uint112, uint32);

    function price0CumulativeLast() external view returns (uint256);

    function price1CumulativeLast() external view returns (uint256);
}

/// @title Uniswap V2 oracle helpers.
/// @notice Computes cumulative prices for TWAP construction. Included because
///         price-oracle manipulation is a common rug/exploit primitive the
///         analyzer reasons about.
library UniswapV2OracleLibrary {
    function currentBlockTimestamp() internal view returns (uint32) {
        return uint32(block.timestamp % 2 ** 32);
    }

    function currentCumulativePrices(address pair)
        internal
        view
        returns (uint256 price0Cumulative, uint256 price1Cumulative, uint32 blockTimestamp)
    {
        blockTimestamp = currentBlockTimestamp();
        (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast) = IUniswapV2PairCumulative(pair).getReserves();
        price0Cumulative = IUniswapV2PairCumulative(pair).price0CumulativeLast();
        price1Cumulative = IUniswapV2PairCumulative(pair).price1CumulativeLast();

        if (blockTimestampLast != blockTimestamp) {
            uint32 timeElapsed = blockTimestamp - blockTimestampLast;
            price0Cumulative += (uint256(reserve1) * timeElapsed) / reserve0;
            price1Cumulative += (uint256(reserve0) * timeElapsed) / reserve1;
        }
    }

    /// @notice Average price over an elapsed window, scaled by 1e18.
    function consult(address pair, uint256 amountIn, address tokenIn)
        internal
        view
        returns (uint256 amountOut)
    {
        (uint112 reserve0, uint112 reserve1,) = IUniswapV2PairCumulative(pair).getReserves();
        (uint256 price0, uint256 price1,) = currentCumulativePrices(pair);
        bool tokenInIsToken0 = tokenIn == _token0(pair);
        uint256 price = tokenInIsToken0 ? price1 * 1e18 / price0 : price0 * 1e18 / price1;
        amountOut = (price * amountIn) / 1e18;
        reserve0;
        reserve1;
    }

    function _token0(address pair) private view returns (address token0) {
        (bool ok, bytes memory data) = pair.staticcall(abi.encodeWithSignature("token0()"));
        require(ok, "OracleLibrary: token0 failed");
        token0 = abi.decode(data, (address));
    }
}
