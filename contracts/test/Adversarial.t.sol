// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {BaseDex} from "./BaseDex.t.sol";
import {HoneypotERC20} from "../src/fixtures/HoneypotERC20.sol";
import {BlacklistERC20} from "../src/fixtures/BlacklistERC20.sol";
import {TradingSwitchERC20} from "../src/fixtures/TradingSwitchERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @notice Adversarial tests: demonstrate how an owner can weaponise privileges
///         after a user has already bought, which is what the risk engine must
///         capture as "owner-controlled" risk rather than mere existence.
contract AdversarialTest is BaseDex {
    function setUp() public {
        _deployDex();
    }

    /// @dev A user buys, then the owner removes sell access -> rug pull path.
    function test_HoneypotOwnerCanTrapBuyer() public {
        HoneypotERC20 token = new HoneypotERC20();
        token.enableTrading();
        _addLiquidityETH(address(token), 100_000 ether, 100 ether);
        token.setPair(factory.getPair(address(token), address(weth)));

        uint256 bought = _buy(address(token), 1 ether);
        assertGt(bought, 0);

        // Owner revokes the trader's ability to sell by disabling trading.
        // (tradingEnabled=false makes even the sell path revert)
        // We simulate by whitelisting only owner, which the token already does.
        assertFalse(token.isWhitelisted(trader));

        address[] memory path = new address[](2);
        path[0] = address(token);
        path[1] = address(weth);
        vm.startPrank(trader);
        IERC20(address(token)).approve(address(router), bought);
        vm.expectRevert(bytes("Sell not allowed"));
        router.swapExactTokensForETH(bought, 0, path, trader, block.timestamp);
        vm.stopPrank();
    }

    /// @dev Blacklist can freeze a holder with no recourse.
    function test_BlacklistFreezesHolder() public {
        BlacklistERC20 token = new BlacklistERC20();
        token.transfer(trader, 100 ether);
        token.addBlacklist(trader);
        vm.prank(trader);
        vm.expectRevert(bytes("Blacklisted"));
        token.transfer(owner, 1 ether);
    }

    /// @dev Trading switch lets the owner halt all transfers.
    function test_TradingSwitchHaltsAllTransfers() public {
        TradingSwitchERC20 token = new TradingSwitchERC20();
        token.enableTrading();
        token.transfer(trader, 100 ether);
        token.disableTrading();
        vm.prank(trader);
        vm.expectRevert(bytes("Trading disabled"));
        token.transfer(owner, 1 ether);
    }
}
