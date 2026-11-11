// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Minimal math helpers (Uniswap V2 compatible).
library SafeMath {
    function add(uint256 x, uint256 y) internal pure returns (uint256) {
        return x + y;
    }

    function sub(uint256 x, uint256 y) internal pure returns (uint256) {
        require(y <= x, "SafeMath: subtraction underflow");
        return x - y;
    }

    function mul(uint256 x, uint256 y) internal pure returns (uint256) {
        return x * y;
    }
}

library Math {
    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }

    /// @dev Babylonian square root.
    function sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }
}
