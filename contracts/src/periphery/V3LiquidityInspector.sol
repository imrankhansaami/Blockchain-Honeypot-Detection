// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IUniswapV3Factory} from "../interfaces/IUniswapV3Factory.sol";
import {IUniswapV3Pool} from "../interfaces/IUniswapV3Pool.sol";

/// @title Uniswap V3 liquidity inspector.
/// @notice Read-only helper that reports the liquidity of a V3 pool for a token
///         pair across the standard fee tiers. Used to decide whether a V3 route
///         exists before attempting simulation, without trusting off-chain data.
contract V3LiquidityInspector {
    uint24 public constant FEE_LOW = 500;
    uint24 public constant FEE_MEDIUM = 3000;
    uint24 public constant FEE_HIGH = 10_000;

    struct PoolInfo {
        uint24 fee;
        address pool;
        uint128 liquidity;
        int24 tick;
        bool initialized;
    }

    struct Report {
        address token;
        address quote;
        uint128 totalLiquidity;
        PoolInfo[] pools;
    }

    function inspect(address factory, address token, address quote) external view returns (Report memory report) {
        report.token = token;
        report.quote = quote;
        uint24[3] memory fees = [FEE_LOW, FEE_MEDIUM, FEE_HIGH];
        report.pools = new PoolInfo[](3);

        for (uint256 i; i < fees.length; i++) {
            address pool = IUniswapV3Factory(factory).getPool(token, quote, fees[i]);
            PoolInfo memory info = PoolInfo({fee: fees[i], pool: pool, liquidity: 0, tick: 0, initialized: false});
            if (pool != address(0)) {
                (, int24 tick,,,,,) = IUniswapV3Pool(pool).slot0();
                uint128 liquidity = IUniswapV3Pool(pool).liquidity();
                info.liquidity = liquidity;
                info.tick = tick;
                info.initialized = true;
                report.totalLiquidity += liquidity;
            }
            report.pools[i] = info;
        }
    }
}
