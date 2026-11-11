// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {FeeRedirectToken} from "../src/fixtures/FeeRedirectToken.sol";
import {HiddenMintToken} from "../src/fixtures/HiddenMintToken.sol";
import {CooldownToken} from "../src/fixtures/CooldownToken.sol";
import {LiquidityPullToken} from "../src/fixtures/LiquidityPullToken.sol";
import {ObfuscatedBlocklistToken} from "../src/fixtures/ObfuscatedBlocklistToken.sol";
import {StandardERC20} from "../src/fixtures/StandardERC20.sol";

import {BatchTransfer} from "../src/periphery/BatchTransfer.sol";
import {RewardsDistributor} from "../src/periphery/RewardsDistributor.sol";
import {Multicall} from "../src/periphery/Multicall.sol";
import {TokenBuyback} from "../src/periphery/TokenBuyback.sol";
import {TokenVesting} from "../src/periphery/TokenVesting.sol";

import {PausableToken} from "../src/standards/PausableToken.sol";
import {FlashMintToken} from "../src/standards/FlashMintToken.sol";
import {ERC1363Token} from "../src/standards/ERC1363Token.sol";
import {SimpleGovernor} from "../src/governance/SimpleGovernor.sol";

contract PatternsTest is Test {
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    receive() external payable {}

    // --- fixtures ---

    function test_FeeRedirect_TakesSellFee() public {
        FeeRedirectToken token = new FeeRedirectToken(alice);
        token.setPair(bob);
        token.transfer(bob, 1_000 ether);
        assertEq(token.balanceOf(alice), 50 ether); // 5% sell fee
        assertEq(token.balanceOf(bob), 950 ether);
    }

    function test_FeeRedirect_RecipientOnlyOwner() public {
        FeeRedirectToken token = new FeeRedirectToken(alice);
        vm.prank(alice);
        vm.expectRevert();
        token.setFeeRecipient(bob);
    }

    function test_HiddenMint_MintsViaInnocuousName() public {
        HiddenMintToken token = new HiddenMintToken();
        uint256 before = token.totalSupply();
        token.syncLiquidity(alice, 1_000 ether);
        assertEq(token.totalSupply(), before + 1_000 ether);
        assertEq(token.balanceOf(alice), 1_000 ether);
    }

    function test_HiddenMint_RespectsCap() public {
        HiddenMintToken token = new HiddenMintToken();
        vm.expectRevert(bytes("HiddenMintToken: cap"));
        token.processFees(alice, 10_000_000 ether);
    }

    function test_Cooldown_BlocksRapidTransfers() public {
        CooldownToken token = new CooldownToken();
        token.transfer(alice, 1_000 ether);
        vm.warp(block.timestamp + 100);
        vm.prank(alice);
        token.transfer(bob, 1 ether);
        vm.prank(alice);
        vm.expectRevert(bytes("CooldownToken: cooldown"));
        token.transfer(bob, 1 ether);
    }

    function test_LiquidityPull_DrainsPool() public {
        StandardERC20 lp = new StandardERC20();
        LiquidityPullToken token = new LiquidityPullToken();
        lp.transfer(address(token), 500 ether);
        token.setPair(address(lp));

        token.pullLiquidity();
        assertEq(lp.balanceOf(address(token)), 0);
        assertEq(lp.balanceOf(address(this)), 1_000_000 ether);
    }

    function test_LiquidityPull_CannotPullWhenLocked() public {
        StandardERC20 lp = new StandardERC20();
        LiquidityPullToken token = new LiquidityPullToken();
        lp.transfer(address(token), 500 ether);
        token.setPair(address(lp));
        token.lockLiquidity();
        vm.expectRevert(bytes("LiquidityPullToken: locked"));
        token.pullLiquidity();
    }

    function test_ObfuscatedBlocklist_BlocksFlaggedAccount() public {
        ObfuscatedBlocklistToken token = new ObfuscatedBlocklistToken();
        token.transfer(alice, 100 ether);
        token.setFlag(alice, 1);
        assertTrue(token.isBlocked(alice));
        vm.prank(alice);
        vm.expectRevert(bytes("OBF: account restricted"));
        token.transfer(bob, 1 ether);
    }

    // --- periphery ---

    function test_BatchTransfer_EqualAmounts() public {
        StandardERC20 token = new StandardERC20();
        BatchTransfer batch = new BatchTransfer();
        token.approve(address(batch), 100 ether);

        address[] memory recipients = new address[](2);
        recipients[0] = alice;
        recipients[1] = bob;
        batch.batchEqual(IERC20(address(token)), recipients, 10 ether);

        assertEq(token.balanceOf(alice), 10 ether);
        assertEq(token.balanceOf(bob), 10 ether);
    }

    function test_RewardsDistributor_Proportional() public {
        StandardERC20 token = new StandardERC20();
        RewardsDistributor distributor = new RewardsDistributor(address(this));
        token.transfer(address(distributor), 100 ether);

        RewardsDistributor.Share[] memory list = new RewardsDistributor.Share[](2);
        list[0] = RewardsDistributor.Share({account: alice, weight: 1});
        list[1] = RewardsDistributor.Share({account: bob, weight: 3});
        distributor.setShares(list);
        distributor.distribute(IERC20(address(token)));

        assertEq(token.balanceOf(alice), 25 ether);
        assertEq(token.balanceOf(bob), 75 ether);
    }

    function test_Multicall_AggregatesCalls() public {
        StandardERC20 token = new StandardERC20();
        Multicall multicall = new Multicall();

        Multicall.Call[] memory calls = new Multicall.Call[](2);
        calls[0] = Multicall.Call({target: address(token), data: abi.encodeWithSignature("totalSupply()"), value: 0});
        calls[1] = Multicall.Call({target: address(token), data: abi.encodeWithSignature("symbol()"), value: 0});

        (bytes[] memory results, bool[] memory successes) = multicall.aggregate(calls, true);
        assertTrue(successes[0] && successes[1]);
        assertEq(abi.decode(results[0], (uint256)), 1_000_000 ether);
    }

    function test_TokenBuyback_RecoversOtherTokens() public {
        StandardERC20 token = new StandardERC20();
        StandardERC20 other = new StandardERC20();
        TokenBuyback buyback = new TokenBuyback(address(token), address(0), address(0));

        other.transfer(address(buyback), 100 ether);
        buyback.recoverToken(IERC20(address(other)), 100 ether);
        assertEq(other.balanceOf(address(this)), 1_000_000 ether);

        vm.expectRevert(bytes("TokenBuyback: cannot recover buyback token"));
        buyback.recoverToken(IERC20(address(token)), 0);
    }

    // --- standards / governance ---

    function test_PausableToken_PauseBlocksTransfers() public {
        PausableToken token = new PausableToken();
        token.pause();
        vm.expectRevert();
        token.transfer(alice, 1 ether);
        token.unpause();
        token.transfer(alice, 1 ether);
        assertEq(token.balanceOf(alice), 1 ether);
    }

    function test_FlashMint_ZeroFee() public {
        FlashMintToken token = new FlashMintToken();
        assertEq(token.flashFee(address(token), 1_000 ether), 0);
    }

    function test_ERC1363_Transfers() public {
        ERC1363Token token = new ERC1363Token();
        token.transfer(alice, 100 ether);
        assertEq(token.balanceOf(alice), 100 ether);
    }

    function test_Governor_ProposeVoteExecute() public {
        StandardERC20 token = new StandardERC20();
        SimpleGovernor governor = new SimpleGovernor(address(token), 1_000 ether, 100);

        uint256 id = governor.propose(alice, 0, "");
        vm.roll(block.number + 2);
        governor.castVote(id, true);
        vm.roll(block.number + 101);

        governor.execute(id);
        assertTrue(governor.getProposal(id).executed);
    }
}
