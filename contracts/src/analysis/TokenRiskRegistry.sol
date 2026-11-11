// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {HoneypotPatterns} from "./HoneypotPatterns.sol";

/// @title On-chain token risk registry.
/// @notice Analysts publish pattern observations for a token; consumers can read
///         an aggregated severity. Mirrors the off-chain report so the taxonomy
///         is usable on-chain.
contract TokenRiskRegistry {
    struct Observation {
        bytes32 pattern;
        uint16 severityBps;
        string note;
        uint64 observedAt;
        address analyst;
    }

    address public admin;
    mapping(address => address[]) public observers; // token => observers
    mapping(address => Observation[]) private _observations;

    event ObserverAdded(address indexed token, address indexed observer);
    event ObservationRecorded(address indexed token, bytes32 indexed pattern, uint16 severityBps, address analyst);

    modifier onlyAdmin() {
        require(msg.sender == admin, "TokenRiskRegistry: not admin");
        _;
    }

    modifier onlyObserver(address token) {
        bool allowed = msg.sender == admin;
        if (!allowed) {
            address[] storage list = observers[token];
            for (uint256 i; i < list.length; i++) {
                if (list[i] == msg.sender) {
                    allowed = true;
                    break;
                }
            }
        }
        require(allowed, "TokenRiskRegistry: not observer");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function addObserver(address token, address observer) external onlyAdmin {
        observers[token].push(observer);
        emit ObserverAdded(token, observer);
    }

    function record(address token, bytes32 pattern, string calldata note) external onlyObserver(token) {
        uint16 severity = HoneypotPatterns.severityOf(pattern);
        _observations[token].push(
            Observation({
                pattern: pattern,
                severityBps: severity,
                note: note,
                observedAt: uint64(block.timestamp),
                analyst: msg.sender
            })
        );
        emit ObservationRecorded(token, pattern, severity, msg.sender);
    }

    function observationCount(address token) external view returns (uint256) {
        return _observations[token].length;
    }

    function observationAt(address token, uint256 index) external view returns (Observation memory) {
        return _observations[token][index];
    }

    /// @notice Highest observed severity for a token (0 if none).
    function highestSeverity(address token) external view returns (uint16 highest) {
        Observation[] storage list = _observations[token];
        for (uint256 i; i < list.length; i++) {
            if (list[i].severityBps > highest) {
                highest = list[i].severityBps;
            }
        }
    }
}
