// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {RebaseToken} from "../src/tokens/RebaseToken.sol";
import {DeflationaryToken} from "../src/tokens/DeflationaryToken.sol";
import {AntiBotToken} from "../src/tokens/AntiBotToken.sol";
import {PresaleToken} from "../src/tokens/PresaleToken.sol";
import {ReflectionToken} from "../src/tokens/ReflectionToken.sol";
import {BondingCurveToken} from "../src/tokens/BondingCurveToken.sol";
import {PermitToken} from "../src/tokens/PermitToken.sol";
import {GovernanceToken} from "../src/tokens/GovernanceToken.sol";
import {MultiSigWallet} from "../src/access/MultiSigWallet.sol";
import {LiquidityLocker} from "../src/periphery/LiquidityLocker.sol";
import {TokenVesting} from "../src/periphery/TokenVesting.sol";
import {FeeSplitter} from "../src/periphery/FeeSplitter.sol";
import {StandardERC20} from "../src/fixtures/StandardERC20.sol";

contract AdvancedTokensTest is Test {
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    receive() external payable {}

    // --- RebaseToken ---

    function test_Rebase_ScalesBalances() public {
        RebaseToken token = new RebaseToken();
        uint256 before = token.balanceOf(address(this));
        token.rebase(2e18);
        assertEq(token.balanceOf(address(this)), before * 2);
        assertEq(token.multiplier(), 2e18);
    }

    function test_Rebase_OnlyOwner() public {
        RebaseToken token = new RebaseToken();
        vm.prank(alice);
        vm.expectRevert();
        token.rebase(3e18);
    }

    // --- DeflationaryToken ---

    function test_Deflationary_BurnsOnTransfer() public {
        DeflationaryToken token = new DeflationaryToken(500); // 5%
        token.transfer(alice, 1000 ether);
        assertEq(token.balanceOf(alice), 950 ether);
        assertEq(token.balanceOf(token.BURN_ADDRESS()), 50 ether);
    }

    // --- AntiBotToken ---

    function test_AntiBot_MaxTxEnforced() public {
        AntiBotToken token = new AntiBotToken();
        token.transfer(alice, 900_000 ether); // owner is exempt
        vm.prank(alice);
        vm.expectRevert(bytes("AntiBotToken: max tx exceeded"));
        token.transfer(bob, 20_000 ether);
    }

    function test_AntiBot_OwnerIsExempt() public {
        AntiBotToken token = new AntiBotToken();
        token.transfer(alice, 900_000 ether);
        assertEq(token.balanceOf(alice), 900_000 ether);
    }

    // --- PresaleToken ---

    function test_Presale_TradingGateAndTax() public {
        PresaleToken token = new PresaleToken(address(0xFEE), address(0x999));
        vm.prank(alice);
        vm.expectRevert(bytes("PresaleToken: trading disabled"));
        token.transfer(bob, 1 ether);

        token.enableTrading();
        token.setTaxes(0, 1000);
        assertTrue(token.tradingEnabled());
        assertEq(token.sellTaxBps(), 1000);
    }

    function test_Presale_RoleGated() public {
        PresaleToken token = new PresaleToken(address(0xFEE), address(0x999));
        vm.prank(alice);
        vm.expectRevert();
        token.setTaxes(100, 100);
    }

    // --- ReflectionToken ---

    function test_Reflection_AccruesAndClaims() public {
        ReflectionToken token = new ReflectionToken();
        token.transfer(alice, 500_000 ether); // fee accrues to pool
        assertGt(token.rewardPool(), 0);

        vm.prank(alice);
        uint256 claimed = token.claim();
        assertGt(claimed, 0);
        assertEq(token.balanceOf(alice), 485_000 ether + claimed);
    }

    // --- BondingCurveToken ---

    function test_BondingCurve_BuyAndSell() public {
        BondingCurveToken token = new BondingCurveToken(1e12, 0);
        uint256 amount = token.buy{value: 1 ether}();
        assertGt(amount, 0);
        assertEq(token.balanceOf(address(this)), amount);

        uint256 refund = token.sell(amount);
        assertEq(refund, 1 ether); // flat curve, no fees
        assertEq(token.balanceOf(address(this)), 0);
    }

    // --- PermitToken / GovernanceToken ---

    function test_Permit_MintRespectsCap() public {
        PermitToken token = new PermitToken(1_000 ether, 2_000 ether);
        token.mint(alice, 1_000 ether);
        vm.expectRevert(bytes("PermitToken: cap exceeded"));
        token.mint(alice, 1 ether);
    }

    function test_Governance_MintCapAndVotes() public {
        GovernanceToken token = new GovernanceToken(1_000 ether, 1_500 ether);
        token.mint(alice, 500 ether);
        vm.expectRevert(bytes("GovernanceToken: cap exceeded"));
        token.mint(alice, 1 ether);

        token.delegate(address(this));
        vm.roll(block.number + 2);
        assertEq(token.getVotes(address(this)), token.balanceOf(address(this)));
    }

    function test_Governance_PauseRole() public {
        GovernanceToken token = new GovernanceToken(1_000 ether, 1_500 ether);
        token.setTransfersPaused(true);
        vm.expectRevert(bytes("GovernanceToken: paused"));
        token.transfer(alice, 1 ether);
    }

    // --- MultiSigWallet ---

    function test_MultiSig_RequiresThreshold() public {
        address[] memory owners = new address[](3);
        owners[0] = address(this);
        owners[1] = alice;
        owners[2] = bob;
        MultiSigWallet wallet = new MultiSigWallet(owners, 2);
        vm.deal(address(wallet), 10 ether);

        uint256 txId = wallet.submit(bob, 1 ether, "");
        wallet.confirm(txId);
        vm.prank(alice);
        wallet.confirm(txId);

        uint256 before = bob.balance;
        wallet.execute(txId);
        assertEq(bob.balance, before + 1 ether);
    }

    function test_MultiSig_BlocksSingleConfirmation() public {
        address[] memory owners = new address[](2);
        owners[0] = address(this);
        owners[1] = alice;
        MultiSigWallet wallet = new MultiSigWallet(owners, 2);
        vm.deal(address(wallet), 1 ether);

        uint256 txId = wallet.submit(alice, 1 ether, "");
        wallet.confirm(txId);
        vm.expectRevert(bytes("MultiSigWallet: not enough confirmations"));
        wallet.execute(txId);
    }

    // --- LiquidityLocker ---

    function test_LiquidityLocker_EnforcesUnlock() public {
        StandardERC20 token = new StandardERC20();
        LiquidityLocker locker = new LiquidityLocker(address(this));
        token.approve(address(locker), 1_000 ether);
        uint64 unlock = uint64(block.timestamp + 100);
        uint256 id = locker.lock(address(token), 1_000 ether, unlock);

        vm.expectRevert(bytes("LiquidityLocker: still locked"));
        locker.withdraw(id);

        vm.warp(unlock + 1);
        locker.withdraw(id);
        assertEq(token.balanceOf(address(this)), 1_000_000 ether);
    }

    // --- TokenVesting ---

    function test_TokenVesting_LinearRelease() public {
        StandardERC20 token = new StandardERC20();
        TokenVesting vesting = new TokenVesting(address(this));
        token.transfer(address(vesting), 1_000 ether);

        uint64 start = uint64(block.timestamp);
        vesting.createSchedule(bytes32("s1"), alice, 1_000 ether, start, start, 100, false);

        assertEq(vesting.releasable(bytes32("s1")), 0);
        vm.warp(start + 50);
        vm.prank(alice);
        vesting.release(bytes32("s1"), token);
        assertEq(token.balanceOf(alice), 500 ether);

        vm.warp(start + 101);
        vm.prank(alice);
        vesting.release(bytes32("s1"), token);
        assertEq(token.balanceOf(alice), 1_000 ether);
    }

    // --- FeeSplitter ---

    function test_FeeSplitter_SplitsNative() public {
        FeeSplitter splitter = new FeeSplitter(address(this));
        FeeSplitter.Recipient[] memory list = new FeeSplitter.Recipient[](2);
        list[0] = FeeSplitter.Recipient({account: alice, bps: 5000});
        list[1] = FeeSplitter.Recipient({account: bob, bps: 5000});
        splitter.setRecipients(list);

        vm.deal(address(this), 1 ether);
        (bool ok,) = address(splitter).call{value: 1 ether}("");
        assertTrue(ok);
        assertEq(alice.balance, 0.5 ether);
        assertEq(bob.balance, 0.5 ether);
    }
}
