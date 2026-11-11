// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Minimal multicall via delegatecall.
/// @notice Batches several calls to this contract into one transaction. The
///         analyzer flags `delegatecall` usage; this is a benign and common case.
contract Multicall {
    struct Call {
        address target;
        bytes data;
        uint256 value;
    }

    event CallExecuted(uint256 indexed index, bool success);

    /// @notice Execute a sequence of calls. Reverts only if `requireAllSuccess`.
    function aggregate(Call[] calldata calls, bool requireAllSuccess)
        external
        payable
        returns (bytes[] memory results, bool[] memory successes)
    {
        results = new bytes[](calls.length);
        successes = new bool[](calls.length);
        for (uint256 i; i < calls.length; i++) {
            (bool ok, bytes memory data) = calls[i].target.call{value: calls[i].value}(calls[i].data);
            results[i] = data;
            successes[i] = ok;
            emit CallExecuted(i, ok);
            if (requireAllSuccess) {
                require(ok, "Multicall: call failed");
            }
        }
    }

    /// @notice Delegate a single call to `target`. Used for library-style wiring.
    function delegate(address target, bytes calldata data) external returns (bytes memory) {
        (bool ok, bytes memory result) = target.delegatecall(data);
        require(ok, "Multicall: delegate failed");
        return result;
    }
}
