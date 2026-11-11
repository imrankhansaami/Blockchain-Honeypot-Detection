// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title English auction with bid refunds and seller withdrawal.
/// @notice Exercises state-machine and outbound-transfer analysis. The final
///         settlement path pays the seller, which the analyzer traces.
contract TokenAuction is ReentrancyGuard {
    using SafeERC20 for IERC20;

    struct Auction {
        address seller;
        IERC20 token;
        uint256 tokenIdOrAmount;
        uint256 reservePrice;
        uint256 highestBid;
        address highestBidder;
        uint64 endTime;
        bool settled;
    }

    mapping(uint256 => Auction) public auctions;
    mapping(uint256 => mapping(address => uint256)) public pendingReturns;

    event AuctionCreated(uint256 indexed id, address indexed seller, uint256 reservePrice, uint64 endTime);
    event BidPlaced(uint256 indexed id, address indexed bidder, uint256 amount);
    event Settled(uint256 indexed id, address indexed winner, uint256 amount);

    function createAuction(
        uint256 id,
        IERC20 token,
        uint256 tokenIdOrAmount,
        uint256 reservePrice,
        uint64 duration
    ) external {
        require(auctions[id].seller == address(0), "TokenAuction: exists");
        require(duration > 0, "TokenAuction: duration");
        token.safeTransferFrom(msg.sender, address(this), tokenIdOrAmount);
        auctions[id] = Auction({
            seller: msg.sender,
            token: token,
            tokenIdOrAmount: tokenIdOrAmount,
            reservePrice: reservePrice,
            highestBid: 0,
            highestBidder: address(0),
            endTime: uint64(block.timestamp) + duration,
            settled: false
        });
        emit AuctionCreated(id, msg.sender, reservePrice, uint64(block.timestamp) + duration);
    }

    function bid(uint256 id) external payable nonReentrant {
        Auction storage auction = auctions[id];
        require(block.timestamp < auction.endTime, "TokenAuction: ended");
        require(msg.value > auction.highestBid && msg.value >= auction.reservePrice, "TokenAuction: bid too low");

        if (auction.highestBidder != address(0)) {
            pendingReturns[id][auction.highestBidder] += auction.highestBid;
        }
        auction.highestBid = msg.value;
        auction.highestBidder = msg.sender;
        emit BidPlaced(id, msg.sender, msg.value);
    }

    function withdrawRefund(uint256 id) external nonReentrant {
        uint256 amount = pendingReturns[id][msg.sender];
        require(amount > 0, "TokenAuction: nothing to withdraw");
        pendingReturns[id][msg.sender] = 0;
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok, "TokenAuction: refund failed");
    }

    function settle(uint256 id) external nonReentrant {
        Auction storage auction = auctions[id];
        require(block.timestamp >= auction.endTime, "TokenAuction: not ended");
        require(!auction.settled, "TokenAuction: settled");
        auction.settled = true;

        if (auction.highestBidder == address(0)) {
            auction.token.safeTransfer(auction.seller, auction.tokenIdOrAmount);
            emit Settled(id, address(0), 0);
            return;
        }
        auction.token.safeTransfer(auction.highestBidder, auction.tokenIdOrAmount);
        (bool ok,) = auction.seller.call{value: auction.highestBid}("");
        require(ok, "TokenAuction: payout failed");
        emit Settled(id, auction.highestBidder, auction.highestBid);
    }
}
