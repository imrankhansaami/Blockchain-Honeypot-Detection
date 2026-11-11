// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {YieldVault} from "../src/defi/YieldVault.sol";
import {StakingRewards} from "../src/defi/StakingRewards.sol";
import {SimpleOracle} from "../src/defi/SimpleOracle.sol";
import {Escrow} from "../src/defi/Escrow.sol";
import {LendingPool} from "../src/defi/LendingPool.sol";
import {FlashLoanProvider, IFlashBorrower} from "../src/defi/FlashLoanProvider.sol";
import {TokenAuction} from "../src/defi/TokenAuction.sol";
import {StandardERC20} from "../src/fixtures/StandardERC20.sol";

contract SimpleBorrower is IFlashBorrower {
    IERC20 public immutable asset;
    FlashLoanProvider public immutable provider;

    constructor(IERC20 _asset, FlashLoanProvider _provider) {
        asset = _asset;
        provider = _provider;
    }

    function onFlashLoan(address, address, uint256 amount, uint256 fee, bytes calldata)
        external
        returns (bytes32)
    {
        asset.approve(address(provider), amount + fee);
        return keccak256("ERC3156FlashBorrower.onFlashLoan");
    }
}

contract DeFiTest is Test {
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    receive() external payable {}

    // --- YieldVault ---

    function test_YieldVault_DepositAndHarvest() public {
        StandardERC20 asset = new StandardERC20();
        YieldVault vault = new YieldVault(IERC20(address(asset)));
        asset.approve(address(vault), 100 ether);
        vault.deposit(100 ether, address(this));
        assertEq(vault.totalAssets(), 100 ether);

        asset.approve(address(vault), 50 ether);
        vault.harvest(50 ether);
        assertEq(vault.totalAssets(), 150 ether);
        assertGt(vault.convertToAssets(vault.balanceOf(address(this))), 100 ether);
    }

    // --- StakingRewards ---

    function test_StakingRewards_StreamsRewards() public {
        StandardERC20 stakeToken = new StandardERC20();
        StandardERC20 rewardToken = new StandardERC20();
        StakingRewards staking = new StakingRewards(address(stakeToken), address(rewardToken));

        rewardToken.transfer(address(staking), 1_000 ether);
        staking.notifyRewardAmount(700 ether);

        stakeToken.transfer(alice, 100 ether);
        vm.startPrank(alice);
        stakeToken.approve(address(staking), 100 ether);
        staking.stake(100 ether);
        vm.stopPrank();

        vm.warp(block.timestamp + 3 days);
        vm.prank(alice);
        staking.getReward();
        assertGt(rewardToken.balanceOf(alice), 0);
    }

    // --- SimpleOracle ---

    function test_Oracle_StalenessAndAuthorization() public {
        SimpleOracle oracle = new SimpleOracle(address(this));
        oracle.setUpdater(address(1), alice);

        vm.prank(alice);
        oracle.setPrice(address(1), 2e18);
        assertEq(oracle.getPrice(address(1)), 2e18);

        vm.warp(block.timestamp + 2 hours);
        vm.expectRevert(bytes("SimpleOracle: stale price"));
        oracle.getPrice(address(1));
    }

    function test_Oracle_DeviationGuard() public {
        SimpleOracle oracle = new SimpleOracle(address(this));
        oracle.setPrice(address(1), 1e18);
        vm.expectRevert(bytes("SimpleOracle: deviation too high"));
        oracle.setPrice(address(1), 5e18);
    }

    // --- Escrow ---

    function test_Escrow_ReleaseToSeller() public {
        StandardERC20 token = new StandardERC20();
        Escrow escrow = new Escrow();
        bytes32 id = keccak256("deal-1");

        escrow.createDeal(id, alice, bob, IERC20(address(token)), 100 ether);
        token.approve(address(escrow), 100 ether);
        escrow.fund(id);
        escrow.release(id);

        assertEq(token.balanceOf(alice), 100 ether);
    }

    // --- LendingPool ---

    function test_LendingPool_BorrowAndRepay() public {
        StandardERC20 asset = new StandardERC20();
        LendingPool pool = new LendingPool(address(asset));

        asset.approve(address(pool), 1_000 ether);
        pool.deposit(1_000 ether);
        pool.borrow(500 ether);
        assertGt(asset.balanceOf(address(this)), 500 ether - 1);

        asset.approve(address(pool), 500 ether);
        pool.repay(500 ether);
        assertEq(pool.debtOf(address(this)), 0);
    }

    function test_LendingPool_RejectsOverBorrow() public {
        StandardERC20 asset = new StandardERC20();
        LendingPool pool = new LendingPool(address(asset));
        asset.approve(address(pool), 1_000 ether);
        pool.deposit(1_000 ether);
        vm.expectRevert(bytes("LendingPool: unhealthy"));
        pool.borrow(900 ether); // above 75% LTV
    }

    // --- FlashLoanProvider ---

    function test_FlashLoan_RepaysWithFee() public {
        StandardERC20 asset = new StandardERC20();
        FlashLoanProvider provider = new FlashLoanProvider(address(asset));
        asset.transfer(address(provider), 1_000 ether);

        SimpleBorrower borrower = new SimpleBorrower(IERC20(address(asset)), provider);
        asset.transfer(address(borrower), 10 ether); // cover the fee

        uint256 before = asset.balanceOf(address(provider));
        bool ok = provider.flashLoan(borrower, 100 ether, "");
        assertTrue(ok);
        assertGt(asset.balanceOf(address(provider)), before);
    }

    // --- TokenAuction ---

    function test_TokenAuction_BidAndSettle() public {
        StandardERC20 token = new StandardERC20();
        TokenAuction auction = new TokenAuction();

        token.approve(address(auction), 1_000 ether);
        auction.createAuction(1, IERC20(address(token)), 1_000 ether, 1 ether, 1 hours);

        vm.deal(alice, 5 ether);
        vm.prank(alice);
        auction.bid{value: 2 ether}(1);

        vm.warp(block.timestamp + 2 hours);
        uint256 sellerBefore = address(this).balance;
        auction.settle(1);

        assertEq(token.balanceOf(alice), 1_000 ether);
        assertEq(address(this).balance, sellerBefore + 2 ether);
    }
}
