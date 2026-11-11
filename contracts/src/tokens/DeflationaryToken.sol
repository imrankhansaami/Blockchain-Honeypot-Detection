// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 15 - Deflationary token.
/// @notice Burns a configurable percentage of every transfer, reducing supply.
/// @dev Tests a burn-on-transfer tax that is owner-adjustable.
contract DeflationaryToken is ERC20, Ownable {
    uint256 public burnBps;
    address public constant BURN_ADDRESS = address(0xdead);

    event BurnRateUpdated(uint256 burnBps);

    constructor(uint256 initialBurnBps) ERC20("Deflationary Token", "DEFL") Ownable(msg.sender) {
        require(initialBurnBps <= 2000, "DeflationaryToken: too high");
        burnBps = initialBurnBps;
        _mint(msg.sender, 1_000_000 ether);
    }

    function setBurnBps(uint256 newBurnBps) external onlyOwner {
        require(newBurnBps <= 2000, "DeflationaryToken: too high");
        burnBps = newBurnBps;
        emit BurnRateUpdated(newBurnBps);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0) && burnBps > 0) {
            uint256 burnAmount = (value * burnBps) / 10_000;
            if (burnAmount > 0) {
                super._update(from, BURN_ADDRESS, burnAmount);
            }
            super._update(from, to, value - burnAmount);
        } else {
            super._update(from, to, value);
        }
    }
}
