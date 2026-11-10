// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {UpgradeableTokenV1} from "../src/fixtures/upgradeable/UpgradeableTokenV1.sol";
import {UpgradeableTokenV2} from "../src/fixtures/upgradeable/UpgradeableTokenV2.sol";

/// @notice Proves the UUPS fixture is upgradeable and that a privileged upgrade
///         can introduce arbitrary minting.
contract UpgradeableTest is Test {
    UpgradeableTokenV1 internal implV1;
    UpgradeableTokenV2 internal implV2;
    UpgradeableTokenV1 internal proxy;

    address internal admin = address(this);
    address internal attacker = address(0xBAD);

    function setUp() public {
        implV1 = new UpgradeableTokenV1();
        bytes memory initData = abi.encodeCall(UpgradeableTokenV1.initialize, (admin));
        ERC1967Proxy p = new ERC1967Proxy(address(implV1), initData);
        proxy = UpgradeableTokenV1(address(p));
    }

    function test_ProxyInitializedAsV1() public {
        assertEq(proxy.version(), "v1");
        assertEq(proxy.totalSupply(), 1_000_000 ether);
        assertEq(proxy.owner(), admin);
    }

    function test_NonOwnerCannotUpgrade() public {
        implV2 = new UpgradeableTokenV2();
        bytes memory data = abi.encodeCall(UpgradeableTokenV2.mint, (attacker, 1 ether));
        vm.prank(attacker);
        vm.expectRevert();
        // UUPS: _authorizeUpgrade is onlyOwner -> non-owner reverts.
        proxy.upgradeToAndCall(address(implV2), data);
    }

    function test_OwnerUpgradeIntroducesMinting() public {
        implV2 = new UpgradeableTokenV2();
        bytes memory data = abi.encodeCall(UpgradeableTokenV2.mint, (admin, 500 ether));
        proxy.upgradeToAndCall(address(implV2), data);
        assertEq(proxy.version(), "v2");
        // The upgrade itself can mint new supply -> supply inflation risk.
        assertEq(proxy.totalSupply(), 1_000_000 ether + 500 ether);
    }
}
