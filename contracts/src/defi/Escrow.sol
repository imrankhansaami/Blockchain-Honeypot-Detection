// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title Two-party escrow with an arbiter.
/// @notice Deposits are held until the buyer releases, the arbiter resolves, or
///         the seller refunds. Exercises access-control and reentrancy analysis.
contract Escrow is ReentrancyGuard {
    using SafeERC20 for IERC20;

    enum State {
        AwaitingPayment,
        Funded,
        Released,
        Refunded,
        Disputed
    }

    struct Deal {
        address buyer;
        address seller;
        address arbiter;
        IERC20 token;
        uint256 amount;
        State state;
    }

    mapping(bytes32 => Deal) public deals;

    event DealCreated(bytes32 indexed id, address buyer, address seller, uint256 amount);
    event Funded(bytes32 indexed id);
    event Released(bytes32 indexed id, address indexed to);
    event Refunded(bytes32 indexed id, address indexed to);
    event Disputed(bytes32 indexed id, address indexed raisedBy);

    modifier onlyParty(bytes32 id) {
        Deal storage deal = deals[id];
        require(
            msg.sender == deal.buyer || msg.sender == deal.seller || msg.sender == deal.arbiter,
            "Escrow: not a party"
        );
        _;
    }

    function createDeal(bytes32 id, address seller, address arbiter, IERC20 token, uint256 amount) external {
        require(deals[id].buyer == address(0), "Escrow: exists");
        require(seller != address(0) && arbiter != address(0), "Escrow: zero address");
        deals[id] = Deal({
            buyer: msg.sender,
            seller: seller,
            arbiter: arbiter,
            token: token,
            amount: amount,
            state: State.AwaitingPayment
        });
        emit DealCreated(id, msg.sender, seller, amount);
    }

    function fund(bytes32 id) external nonReentrant {
        Deal storage deal = deals[id];
        require(msg.sender == deal.buyer, "Escrow: not buyer");
        require(deal.state == State.AwaitingPayment, "Escrow: bad state");
        deal.state = State.Funded;
        deal.token.safeTransferFrom(msg.sender, address(this), deal.amount);
        emit Funded(id);
    }

    function release(bytes32 id) external nonReentrant onlyParty(id) {
        Deal storage deal = deals[id];
        require(deal.state == State.Funded || deal.state == State.Disputed, "Escrow: not fundable");
        require(msg.sender == deal.buyer || msg.sender == deal.arbiter, "Escrow: not allowed");
        deal.state = State.Released;
        deal.token.safeTransfer(deal.seller, deal.amount);
        emit Released(id, deal.seller);
    }

    function refund(bytes32 id) external nonReentrant {
        Deal storage deal = deals[id];
        require(deal.state == State.Funded || deal.state == State.Disputed, "Escrow: not refundable");
        require(msg.sender == deal.seller || msg.sender == deal.arbiter, "Escrow: not allowed");
        deal.state = State.Refunded;
        deal.token.safeTransfer(deal.buyer, deal.amount);
        emit Refunded(id, deal.buyer);
    }

    function raiseDispute(bytes32 id) external onlyParty(id) {
        Deal storage deal = deals[id];
        require(deal.state == State.Funded, "Escrow: not disputable");
        deal.state = State.Disputed;
        emit Disputed(id, msg.sender);
    }
}
