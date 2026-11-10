// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {StandardERC20} from "../src/fixtures/StandardERC20.sol";

/// @notice Invariant handlers that drive random transfers.
contract TokenHandler is Test {
    StandardERC20 public token;
    address[] public actors;

    constructor(StandardERC20 _token) {
        token = _token;
        actors.push(address(0xA1));
        actors.push(address(0xA2));
        actors.push(address(0xA3));
        actors.push(address(0xA4));
    }

    function actorCount() external view returns (uint256) {
        return actors.length;
    }

    function transfer(uint256 fromSeed, uint256 toSeed, uint256 amount) public {
        address from = actors[fromSeed % actors.length];
        address to = actors[toSeed % actors.length];
        if (from == to) return;
        uint256 bal = token.balanceOf(from);
        if (bal == 0) return;
        amount = bound(amount, 0, bal);
        vm.prank(from);
        token.transfer(to, amount);
    }
}

/// @notice Invariants for a plain (no-tax, no-restriction) token: supply is
///         constant and the sum of balances always equals total supply.
contract InvariantsTest is Test {
    StandardERC20 internal token;
    TokenHandler internal handler;
    address[] internal actors;

    function setUp() public {
        token = new StandardERC20();
        handler = new TokenHandler(token);
        // Fund all actors through the handler by approving then transferring.
        address[4] memory list = [address(0xA1), address(0xA2), address(0xA3), address(0xA4)];
        for (uint256 i; i < list.length; i++) {
            token.transfer(list[i], 10_000 ether);
            actors.push(list[i]);
        }
        targetContract(address(handler));
        bytes4[] memory selectors = new bytes4[](1);
        selectors[0] = handler.transfer.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
    }

    function invariant_TotalSupplyConstant() public view {
        assertEq(token.totalSupply(), 1_000_000 ether);
    }

    function invariant_BalancesSumEqualsSupply() public view {
        uint256 sum;
        for (uint256 i; i < actors.length; i++) {
            sum += token.balanceOf(actors[i]);
        }
        sum += token.balanceOf(address(this));
        assertEq(sum, token.totalSupply());
    }
}
