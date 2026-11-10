// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Minimal Uniswap V2 pair interface.
interface IUniswapV2Pair {
    function token0() external view returns (address);

    function token1() external view returns (address);

    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);

    function totalSupply() external view returns (uint256);

    function balanceOf(address owner) external view returns (uint256);

    function transfer(address to, uint256 value) external returns (bool);

    function swap(uint256 amount0Out, uint256 amount1Out, address to, bytes calldata data) external;

    function sync() external;

    function mint(address to) external returns (uint256 liquidity);

    function burn(address to) external returns (uint256 amount0, uint256 amount1);
}
