// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {UpgradeableTokenV1} from "./UpgradeableTokenV1.sol";

/// @title Fixture 10 (V2) - Malicious upgrade: adds unrestricted minting.
contract UpgradeableTokenV2 is UpgradeableTokenV1 {
    function version() external pure override returns (string memory) {
        return "v2";
    }

    /// @notice New owner-only mint capability introduced by the upgrade.
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
