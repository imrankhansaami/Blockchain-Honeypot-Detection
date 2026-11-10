// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {BaseDex} from "./BaseDex.t.sol";
import {StandardERC20} from "../src/fixtures/StandardERC20.sol";
import {FeeOnTransferERC20} from "../src/fixtures/FeeOnTransferERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @notice Fuzz tests validating accounting and conservation properties.
contract FuzzTest is BaseDex {
    function setUp() public {
        _deployDex();
    }

    /// @dev Round-trip on a no-tax token must never create value out of nothing.
    function testFuzz_NoTaxRoundTripNeverProfits(uint96 ethIn) public {
        ethIn = uint96(bound(ethIn, 0.001 ether, 5 ether));
        StandardERC20 token = new StandardERC20();
        _addLiquidityETH(address(token), 1_000_000 ether, 200 ether);

        uint256 bought = _buy(address(token), ethIn);
        uint256 ethBack = _sell(address(token), bought);
        assertLe(ethBack, ethIn, "round trip must not create ETH");
    }

    /// @dev Fee-on-transfer receiver always gets strictly less than sent.
    function testFuzz_FeeOnTransferAlwaysDeducts(uint96 amount) public {
        amount = uint96(bound(amount, 1 ether, 100_000 ether));
        FeeOnTransferERC20 token = new FeeOnTransferERC20();
        token.transfer(trader, amount);
        // Fee is floor(amount * 500 / 10000).
        assertEq(token.balanceOf(trader), uint256(amount) - (uint256(amount) * 500) / 10_000);
    }

    /// @dev Standard token supply is conserved across arbitrary transfers.
    function testFuzz_SupplyConserved(address a, address b, uint96 amount) public {
        amount = uint96(bound(amount, 0, 1_000 ether));
        vm.assume(a != address(0) && b != address(0));
        StandardERC20 token = new StandardERC20();
        uint256 supply = token.totalSupply();
        token.transfer(a, amount);
        vm.prank(a);
        token.transfer(b, amount);
        assertEq(token.totalSupply(), supply);
    }
}
