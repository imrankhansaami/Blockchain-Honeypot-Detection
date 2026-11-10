// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {BaseDex} from "./BaseDex.t.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {StandardERC20} from "../src/fixtures/StandardERC20.sol";
import {HoneypotERC20} from "../src/fixtures/HoneypotERC20.sol";
import {AdjustableTaxERC20} from "../src/fixtures/AdjustableTaxERC20.sol";
import {ExcessiveSellTaxERC20} from "../src/fixtures/ExcessiveSellTaxERC20.sol";
import {BlacklistERC20} from "../src/fixtures/BlacklistERC20.sol";
import {WhitelistOnlyERC20} from "../src/fixtures/WhitelistOnlyERC20.sol";
import {MaxTxERC20} from "../src/fixtures/MaxTxERC20.sol";
import {TradingSwitchERC20} from "../src/fixtures/TradingSwitchERC20.sol";
import {MintableERC20} from "../src/fixtures/MintableERC20.sol";
import {FeeOnTransferERC20} from "../src/fixtures/FeeOnTransferERC20.sol";

/// @notice Behavioural verification that each fixture behaves as the detection
///         engine expects. These prove the fixtures are valid inputs.
contract FixturesTest is BaseDex {
    function setUp() public {
        _deployDex();
    }

    function test_Standard_BuyAndSellSucceed() public {
        StandardERC20 token = new StandardERC20();
        token.transfer(owner, 0); // no-op keep compiler honest
        _addLiquidityETH(address(token), 100_000 ether, 100 ether);
        uint256 bought = _buy(address(token), 1 ether);
        assertGt(bought, 0, "buy should succeed");
        uint256 ethBack = _sell(address(token), bought);
        assertGt(ethBack, 0, "sell should succeed");
        // A no-tax token should return most of the value (< 10% round trip).
        assertGt(ethBack, 0.8 ether, "no excessive tax expected");
    }

    function test_Honeypot_BuySucceedsSellReverts() public {
        HoneypotERC20 token = new HoneypotERC20();
        token.enableTrading();
        _addLiquidityETH(address(token), 100_000 ether, 100 ether);
        token.setPair(factory.getPair(address(token), address(weth)));

        uint256 bought = _buy(address(token), 1 ether);
        assertGt(bought, 0, "buy should succeed");

        address[] memory path = new address[](2);
        path[0] = address(token);
        path[1] = address(weth);
        vm.startPrank(trader);
        IERC20(address(token)).approve(address(router), bought);
        vm.expectRevert(bytes("Sell not allowed"));
        router.swapExactTokensForETH(bought, 0, path, trader, block.timestamp);
        vm.stopPrank();
    }

    function test_AdjustableTax_SellTaxApplied() public {
        AdjustableTaxERC20 token = new AdjustableTaxERC20();
        _addLiquidityETH(address(token), 100_000 ether, 100 ether);
        token.setPair(factory.getPair(address(token), address(weth)));
        token.setTaxes(0, 1000); // 10% sell tax

        uint256 bought = _buy(address(token), 1 ether);
        uint256 ethBack = _sell(address(token), bought);
        // 10% sell tax plus ~0.3% AMM fee -> ETH back close to 0.87-0.90.
        assertGt(ethBack, 0.7 ether);
        assertLt(ethBack, 0.95 ether);
    }

    function test_ExcessiveSellTax_NinetyPercent() public {
        ExcessiveSellTaxERC20 token = new ExcessiveSellTaxERC20();
        _addLiquidityETH(address(token), 100_000 ether, 100 ether);
        token.setPair(factory.getPair(address(token), address(weth)));

        uint256 bought = _buy(address(token), 1 ether);
        uint256 ethBack = _sell(address(token), bought);
        // 90% tax means the trader recovers at most ~10% of the ETH value.
        assertLt(ethBack, 0.2 ether, "expected heavy sell tax");
    }

    function test_Blacklist_BlocksTransfer() public {
        BlacklistERC20 token = new BlacklistERC20();
        token.transfer(trader, 100 ether);
        token.addBlacklist(trader);
        vm.prank(trader);
        vm.expectRevert(bytes("Blacklisted"));
        token.transfer(address(0xdead), 1 ether);
    }

    function test_Whitelist_OnlyWhitelistedCanTransfer() public {
        WhitelistOnlyERC20 token = new WhitelistOnlyERC20();
        token.transfer(trader, 100 ether);
        vm.prank(trader);
        vm.expectRevert(bytes("Not whitelisted"));
        token.transfer(address(0xdead), 1 ether);

        token.setWhitelisted(trader, true);
        vm.prank(trader);
        token.transfer(address(0xdead), 1 ether);
        assertEq(token.balanceOf(address(0xdead)), 1 ether);
    }

    function test_MaxTx_RejectsLargeTransfer() public {
        MaxTxERC20 token = new MaxTxERC20();
        vm.expectRevert(bytes("Max tx exceeded"));
        token.transfer(trader, 20_000 ether);
    }

    function test_TradingSwitch_BlocksUntilEnabled() public {
        TradingSwitchERC20 token = new TradingSwitchERC20();
        vm.prank(trader);
        vm.expectRevert(bytes("Trading disabled"));
        token.transfer(address(0xdead), 0);

        // enable
        token.enableTrading();
        token.transfer(trader, 1 ether);
        assertEq(token.balanceOf(trader), 1 ether);
        // disable again blocks
        token.disableTrading();
        vm.prank(trader);
        vm.expectRevert(bytes("Trading disabled"));
        token.transfer(address(0xdead), 1 ether);
    }

    function test_Mintable_OwnerCanMintArbitrary() public {
        MintableERC20 token = new MintableERC20();
        uint256 supplyBefore = token.totalSupply();
        token.mint(trader, 1_000_000 ether);
        assertEq(token.totalSupply(), supplyBefore + 1_000_000 ether);
    }

    function test_FeeOnTransfer_DeductsOnTransfer() public {
        FeeOnTransferERC20 token = new FeeOnTransferERC20();
        uint256 before = token.balanceOf(trader);
        token.transfer(trader, 100 ether);
        // 5% fee means trader receives 95.
        assertEq(token.balanceOf(trader) - before, 95 ether);
    }
}
