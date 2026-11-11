// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";

import {CappedBurnableToken} from "../src/standards/CappedBurnableToken.sol";
import {WrappedNative} from "../src/standards/WrappedNative.sol";
import {ERC721Collection} from "../src/standards/ERC721Collection.sol";
import {ERC1155MultiToken} from "../src/standards/ERC1155MultiToken.sol";
import {HoneypotPatterns, PatternShowcaseToken} from "../src/analysis/HoneypotPatterns.sol";
import {TokenRiskRegistry} from "../src/analysis/TokenRiskRegistry.sol";

contract StandardsTest is Test {
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    receive() external payable {}

    function test_CappedBurnable_RespectsCap() public {
        CappedBurnableToken token = new CappedBurnableToken(1_000 ether);
        assertEq(token.totalSupply(), 1_000 ether);
        assertEq(token.cap(), 1_000 ether);
        token.burn(100 ether);
        assertEq(token.totalSupply(), 900 ether);
    }

    function test_WrappedNative_DepositWithdraw() public {
        WrappedNative weth = new WrappedNative("Wrapped Ether", "WETH");
        weth.deposit{value: 2 ether}();
        assertEq(weth.balanceOf(address(this)), 2 ether);
        assertEq(weth.totalSupply(), 2 ether);
        weth.withdraw(2 ether);
        assertEq(weth.balanceOf(address(this)), 0);
    }

    function test_ERC721_MintAndTransfer() public {
        ERC721Collection nft = new ERC721Collection("Collection", "COL", address(this));
        uint256 tokenId = nft.mint(alice);
        assertEq(nft.ownerOf(tokenId), alice);
        assertEq(nft.balanceOf(alice), 1);

        vm.prank(alice);
        nft.transferFrom(alice, address(this), tokenId);
        assertEq(nft.ownerOf(tokenId), address(this));
    }

    function test_ERC721_OnlyOwnerMints() public {
        ERC721Collection nft = new ERC721Collection("Collection", "COL", address(this));
        vm.prank(alice);
        vm.expectRevert(bytes("ERC721Collection: not owner"));
        nft.mint(alice);
    }

    function test_ERC1155_MintBatchAndTransfer() public {
        ERC1155MultiToken multi = new ERC1155MultiToken("ipfs://", address(this));
        uint256[] memory ids = new uint256[](2);
        ids[0] = 1;
        ids[1] = 2;
        uint256[] memory amounts = new uint256[](2);
        amounts[0] = 10;
        amounts[1] = 20;
        multi.mintBatch(alice, ids, amounts);

        assertEq(multi.balanceOf(alice, 1), 10);
        assertEq(multi.balanceOf(alice, 2), 20);
        assertEq(multi.totalSupply(1), 10);

        vm.prank(alice);
        multi.safeTransferFrom(alice, bob, 1, 5, "");
        assertEq(multi.balanceOf(bob, 1), 5);
    }

    function test_HoneypotPatterns_Severities() public {
        assertEq(HoneypotPatterns.severityOf(HoneypotPatterns.CANNOT_SELL), 10_000);
        assertEq(HoneypotPatterns.severityOf(HoneypotPatterns.LIQUIDITY_PULL), 9_000);
        assertEq(HoneypotPatterns.severityOf(bytes32("UNKNOWN")), 1_000);
        assertGt(bytes(HoneypotPatterns.describe(HoneypotPatterns.OWNER_BLACKLIST)).length, 0);
    }

    function test_PatternShowcaseToken_BlocksSells() public {
        PatternShowcaseToken token = new PatternShowcaseToken();
        token.enableTrading();
        token.setBlacklisted(alice, true);
        vm.prank(alice);
        vm.expectRevert(bytes("PatternShowcaseToken: blacklisted"));
        token.transfer(address(0xBEEF), 1 ether);
    }

    function test_TokenRiskRegistry_RecordsObservations() public {
        TokenRiskRegistry registry = new TokenRiskRegistry();
        registry.record(address(1), HoneypotPatterns.CANNOT_SELL, "observed on fork");
        registry.record(address(1), HoneypotPatterns.TRADING_GATE, "gate present");
        assertEq(registry.observationCount(address(1)), 2);
        assertEq(registry.highestSeverity(address(1)), 10_000);

        vm.prank(alice);
        vm.expectRevert(bytes("TokenRiskRegistry: not observer"));
        registry.record(address(1), HoneypotPatterns.CANNOT_SELL, "nope");
    }
}
