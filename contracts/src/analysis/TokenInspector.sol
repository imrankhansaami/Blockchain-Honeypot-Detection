// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title On-chain token inspector.
/// @notice Performs a safe, non-reverting inspection of an arbitrary token using
///         low-level calls. View metadata is probed with `staticcall`; state
///         entry points are probed with zero-value `call`s so a non-standard
///         token cannot break the inspection. Mirrors the off-chain
///         TokenAnalyzer's surface checks.
contract TokenInspector {
    struct TokenReport {
        address token;
        uint256 codeSize;
        bool isContract;
        bool hasTotalSupply;
        uint256 totalSupply;
        bool hasBalanceOf;
        bool hasTransfer;
        bool hasApprove;
        uint8 decimals;
        bool hasDecimals;
        address owner;
        bool hasOwner;
    }

    function _staticCall(address target, bytes memory data) private view returns (bool, bytes memory) {
        return target.staticcall(data);
    }

    function inspect(address token) external returns (TokenReport memory report) {
        report.token = token;
        report.codeSize = token.code.length;
        report.isContract = report.codeSize > 0;

        (bool ok, bytes memory data) = _staticCall(token, abi.encodeWithSignature("totalSupply()"));
        if (ok && data.length >= 32) {
            report.hasTotalSupply = true;
            report.totalSupply = abi.decode(data, (uint256));
        }

        (ok,) = _staticCall(token, abi.encodeWithSignature("balanceOf(address)", address(this)));
        report.hasBalanceOf = ok;

        (ok,) = _staticCall(token, abi.encodeWithSignature("decimals()"));
        if (ok) {
            report.hasDecimals = true;
        }

        // State entry points: probe with a zero-value call.
        (bool okTransfer,) = token.call(abi.encodeWithSignature("transfer(address,uint256)", address(this), uint256(0)));
        report.hasTransfer = okTransfer;

        (bool okApprove,) = token.call(abi.encodeWithSignature("approve(address,uint256)", address(this), uint256(0)));
        report.hasApprove = okApprove;

        (ok, data) = _staticCall(token, abi.encodeWithSignature("owner()"));
        if (ok && data.length >= 32) {
            report.hasOwner = true;
            report.owner = abi.decode(data, (address));
        }
    }

    /// @notice Best-effort ERC-20 conformance flag.
    function isErc20(address token) external returns (bool) {
        (bool okSupply,) = _staticCall(token, abi.encodeWithSignature("totalSupply()"));
        (bool okBalance,) = _staticCall(token, abi.encodeWithSignature("balanceOf(address)", address(this)));
        (bool okTransfer,) = token.call(abi.encodeWithSignature("transfer(address,uint256)", address(this), uint256(0)));
        return okSupply && okBalance && okTransfer;
    }
}
