// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {MockUniswapV2Pair} from "./MockUniswapV2Pair.sol";

/// @title Simplified Uniswap V2 factory for local simulation.
/// @dev For local testing only. Mirrors the getPair/createPair surface.
contract MockUniswapV2Factory {
    mapping(address => mapping(address => address)) public getPair;
    address[] public allPairs;
    address public feeTo;

    event PairCreated(address indexed token0, address indexed token1, address pair, uint256);

    function allPairsLength() external view returns (uint256) {
        return allPairs.length;
    }

    function createPair(address tokenA, address tokenB) external returns (address pair) {
        require(tokenA != tokenB, "MockFactory: IDENTICAL_ADDRESSES");
        (address token0, address token1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
        require(token0 != address(0), "MockFactory: ZERO_ADDRESS");
        require(getPair[token0][token1] == address(0), "MockFactory: PAIR_EXISTS");

        MockUniswapV2Pair p = new MockUniswapV2Pair();
        p.initialize(token0, token1);
        pair = address(p);

        getPair[token0][token1] = pair;
        getPair[token1][token0] = pair;
        allPairs.push(pair);
        emit PairCreated(token0, token1, pair, allPairs.length);
    }
}
