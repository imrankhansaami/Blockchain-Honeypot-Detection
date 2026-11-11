// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {MockWETH} from "../src/mocks/MockWETH.sol";
import {MockUniswapV2Factory} from "../src/mocks/MockUniswapV2Factory.sol";
import {MockUniswapV2Router02} from "../src/mocks/MockUniswapV2Router02.sol";
import {StandardERC20} from "../src/fixtures/StandardERC20.sol";

import {PoolInspector} from "../src/analysis/PoolInspector.sol";
import {TokenInspector} from "../src/analysis/TokenInspector.sol";
import {SoulboundToken} from "../src/tokens/SoulboundToken.sol";
import {DividendToken} from "../src/tokens/DividendToken.sol";
import {StakingPool} from "../src/periphery/StakingPool.sol";
import {BondingDeposit} from "../src/periphery/BondingDeposit.sol";
import {TimelockVault} from "../src/periphery/TimelockVault.sol";
import {LinearVotingToken} from "../src/governance/LinearVotingToken.sol";

contract MoreContractsTest is Test {
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    receive() external payable {}

    function test_PoolInspector_ReportsLiquidity() public {
        MockWETH weth = new MockWETH();
        MockUniswapV2Factory factory = new MockUniswapV2Factory();
        MockUniswapV2Router02 router = new MockUniswapV2Router02(address(factory), address(weth));
        StandardERC20 token = new StandardERC20();

        token.approve(address(router), 1_000 ether);
        router.addLiquidityETH{value: 1 ether}(address(token), 1_000 ether, 0, 0, address(this), block.timestamp);

        PoolInspector inspector = new PoolInspector();
        PoolInspector.PoolReport memory report = inspector.inspect(address(factory), address(token), address(weth));
        assertTrue(report.exists);
        assertGt(uint256(report.reserve0), 0);
        assertGt(uint256(report.reserve1), 0);
        assertGt(report.k, 0);
        assertTrue(inspector.hasLiquidity(address(factory), address(token), address(weth)));
    }

    function test_TokenInspector_DetectsSurface() public {
        StandardERC20 token = new StandardERC20();
        TokenInspector inspector = new TokenInspector();
        TokenInspector.TokenReport memory report = inspector.inspect(address(token));
        assertTrue(report.isContract);
        assertTrue(report.hasTotalSupply);
        assertEq(report.totalSupply, 1_000_000 ether);
        assertTrue(report.hasBalanceOf);
        assertTrue(report.hasTransfer);
        assertFalse(report.hasOwner);
        assertTrue(inspector.isErc20(address(token)));
    }

    function test_Soulbound_RejectsTransfers() public {
        SoulboundToken token = new SoulboundToken();
        token.mint(alice, 100 ether);
        assertEq(token.balanceOf(alice), 100 ether);
        vm.prank(alice);
        vm.expectRevert(bytes("SoulboundToken: non-transferable"));
        token.transfer(bob, 1 ether);
    }

    function test_DividendToken_DistributesProRata() public {
        StandardERC20 div = new StandardERC20();
        DividendToken token = new DividendToken(address(div));
        token.transfer(alice, 500_000 ether);

        div.approve(address(token), 100 ether);
        token.distributeDividends(100 ether);

        assertEq(token.totalDividendsDistributed(), 100 ether);
        assertApproxEqAbs(token.withdrawableDividendOf(alice), 50 ether, 1);

        vm.prank(alice);
        token.withdrawDividend();
        assertApproxEqAbs(div.balanceOf(alice), 50 ether, 1);
    }

    function test_StakingPool_AccruesAndClaims() public {
        StandardERC20 stakeToken = new StandardERC20();
        StandardERC20 rewardToken = new StandardERC20();
        StakingPool pool = new StakingPool(address(stakeToken), address(rewardToken), 1e15);

        rewardToken.transfer(address(pool), 1_000 ether);
        stakeToken.transfer(alice, 100 ether);
        vm.startPrank(alice);
        stakeToken.approve(address(pool), 100 ether);
        pool.stake(100 ether);
        vm.stopPrank();

        vm.warp(block.timestamp + 1_000);
        assertGt(pool.pendingReward(alice), 0);

        vm.prank(alice);
        pool.claim();
        assertGt(rewardToken.balanceOf(alice), 0);
    }

    function test_BondingDeposit_VestsLinear() public {
        StandardERC20 token = new StandardERC20();
        StandardERC20 quote = new StandardERC20();
        BondingDeposit deposit = new BondingDeposit(address(token), address(quote), 1e18);

        token.transfer(address(deposit), 1_000 ether);
        deposit.setSaleOpen(true);
        deposit.setVestingDuration(100);

        quote.approve(address(deposit), 10 ether);
        uint256 tokensOut = deposit.deposit(10 ether);
        assertEq(tokensOut, 10 ether);
        assertEq(deposit.claimable(address(this)), 0);

        vm.warp(block.timestamp + 101);
        deposit.claim();
        assertEq(token.balanceOf(address(this)), 999_000 ether + 10 ether);
        assertEq(deposit.totalRaised(), 10 ether);
    }

    function test_TimelockVault_EnforcesUnlock() public {
        StandardERC20 token = new StandardERC20();
        TimelockVault vault = new TimelockVault(address(token));
        token.approve(address(vault), 100 ether);

        uint64 unlock = uint64(block.timestamp + 100);
        uint256 id = vault.lock(100 ether, unlock);

        vm.expectRevert(bytes("TimelockVault: still locked"));
        vault.release(id);

        vm.warp(unlock + 1);
        vault.release(id);
        assertEq(token.balanceOf(address(this)), 1_000_000 ether);
    }

    function test_LinearVoting_DelegationAndCheckpoints() public {
        LinearVotingToken token = new LinearVotingToken();
        token.delegate(address(this));
        assertEq(token.votesOf(address(this)), token.balanceOf(address(this)));

        token.transfer(alice, 100 ether);
        assertEq(token.votesOf(address(this)), 1_000_000 ether - 100 ether);

        uint256 blockNumber = block.number;
        vm.roll(block.number + 5);
        assertEq(token.getPastVotes(address(this), blockNumber), 1_000_000 ether - 100 ether);
    }
}
