// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title Minimal token-weighted governor.
/// @notice Proposals are created by holders above a threshold, voted on by token
///         weight over a fixed period, then executed by anyone. Demonstrates a
///         legitimate, transparent governance flow over a token.
contract SimpleGovernor {
    struct Proposal {
        address proposer;
        address target;
        uint256 value;
        bytes data;
        uint256 forVotes;
        uint256 againstVotes;
        uint64 startBlock;
        uint64 endBlock;
        bool executed;
    }

    ERC20 public immutable token;
    uint256 public proposalThreshold;
    uint64 public votingPeriod;

    Proposal[] private _proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event ProposalCreated(uint256 indexed id, address indexed proposer, address target);
    event VoteCast(uint256 indexed id, address indexed voter, bool support, uint256 weight);
    event ProposalExecuted(uint256 indexed id);

    constructor(address _token, uint256 _threshold, uint64 _votingPeriod) {
        token = ERC20(_token);
        proposalThreshold = _threshold;
        votingPeriod = _votingPeriod;
    }

    function proposalCount() external view returns (uint256) {
        return _proposals.length;
    }

    function getProposal(uint256 id) external view returns (Proposal memory) {
        return _proposals[id];
    }

    function propose(address target, uint256 value, bytes calldata data) external returns (uint256 id) {
        require(token.balanceOf(msg.sender) >= proposalThreshold, "SimpleGovernor: below threshold");
        id = _proposals.length;
        _proposals.push(
            Proposal({
                proposer: msg.sender,
                target: target,
                value: value,
                data: data,
                forVotes: 0,
                againstVotes: 0,
                startBlock: uint64(block.number + 1),
                endBlock: uint64(block.number + 1 + votingPeriod),
                executed: false
            })
        );
        emit ProposalCreated(id, msg.sender, target);
    }

    function castVote(uint256 id, bool support) external {
        Proposal storage proposal = _proposals[id];
        require(block.number >= proposal.startBlock, "SimpleGovernor: not started");
        require(block.number <= proposal.endBlock, "SimpleGovernor: ended");
        require(!hasVoted[id][msg.sender], "SimpleGovernor: already voted");

        uint256 weight = token.balanceOf(msg.sender);
        hasVoted[id][msg.sender] = true;
        if (support) {
            proposal.forVotes += weight;
        } else {
            proposal.againstVotes += weight;
        }
        emit VoteCast(id, msg.sender, support, weight);
    }

    function execute(uint256 id) external payable {
        Proposal storage proposal = _proposals[id];
        require(!proposal.executed, "SimpleGovernor: executed");
        require(block.number > proposal.endBlock, "SimpleGovernor: voting ongoing");
        require(proposal.forVotes > proposal.againstVotes, "SimpleGovernor: not passed");

        proposal.executed = true;
        (bool ok,) = proposal.target.call{value: proposal.value}(proposal.data);
        require(ok, "SimpleGovernor: execution failed");
        emit ProposalExecuted(id);
    }

    receive() external payable {}
}
