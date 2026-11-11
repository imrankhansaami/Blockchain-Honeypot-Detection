// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Push oracle with staleness and deviation guards.
/// @notice The owner pushes prices. The analyzer should recognise the trust
///         assumption: a single updater can move every dependent price.
contract SimpleOracle is Ownable {
    struct PriceData {
        uint256 price; // scaled by 1e18
        uint64 updatedAt;
    }

    mapping(address => PriceData) private _prices;
    mapping(address => address) public updater;
    uint64 public maxAge = 1 hours;
    uint256 public maxDeviationBps = 2000; // 20%

    event PriceUpdated(address indexed asset, uint256 price, uint64 timestamp);
    event UpdaterSet(address indexed asset, address updater);

    constructor(address initialOwner) Ownable(initialOwner) {}

    function setMaxAge(uint64 newMaxAge) external onlyOwner {
        maxAge = newMaxAge;
    }

    function setMaxDeviation(uint256 bps) external onlyOwner {
        require(bps <= 10_000, "SimpleOracle: bps");
        maxDeviationBps = bps;
    }

    function setUpdater(address asset, address account) external onlyOwner {
        updater[asset] = account;
        emit UpdaterSet(asset, account);
    }

    function setPrice(address asset, uint256 price) external {
        require(msg.sender == updater[asset] || msg.sender == owner(), "SimpleOracle: not authorised");
        require(price > 0, "SimpleOracle: zero price");
        PriceData memory current = _prices[asset];
        if (current.price != 0) {
            uint256 diff = price > current.price ? price - current.price : current.price - price;
            require((diff * 10_000) / current.price <= maxDeviationBps, "SimpleOracle: deviation too high");
        }
        _prices[asset] = PriceData({price: price, updatedAt: uint64(block.timestamp)});
        emit PriceUpdated(asset, price, uint64(block.timestamp));
    }

    function getPrice(address asset) external view returns (uint256) {
        PriceData memory data = _prices[asset];
        require(data.price != 0, "SimpleOracle: no price");
        require(block.timestamp <= data.updatedAt + maxAge, "SimpleOracle: stale price");
        return data.price;
    }

    function peekPrice(address asset) external view returns (uint256 price, uint64 updatedAt, bool fresh) {
        PriceData memory data = _prices[asset];
        return (data.price, data.updatedAt, data.price != 0 && block.timestamp <= data.updatedAt + maxAge);
    }
}
