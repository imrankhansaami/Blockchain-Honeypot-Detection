// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fee splitter.
/// @notice Receives native currency and ERC-20 fees from a token and distributes
///         them to configured recipients by basis points. Common in "marketing /
///         liquidity / treasury" tax tokens; a useful privilege to surface.
contract FeeSplitter is Ownable {
    using SafeERC20 for IERC20;

    struct Recipient {
        address account;
        uint256 bps;
    }

    Recipient[] private _recipients;
    uint256 private _totalBps;

    event Distributed(address indexed token, uint256 totalAmount);
    event RecipientsUpdated(uint256 count);

    constructor(address initialOwner) Ownable(initialOwner) {}

    receive() external payable {
        _splitNative(msg.value);
    }

    function recipients() external view returns (Recipient[] memory) {
        return _recipients;
    }

    function setRecipients(Recipient[] calldata list) external onlyOwner {
        delete _recipients;
        uint256 total;
        for (uint256 i; i < list.length; i++) {
            require(list[i].account != address(0), "FeeSplitter: zero account");
            total += list[i].bps;
            _recipients.push(list[i]);
        }
        require(total <= 10_000, "FeeSplitter: bps overflow");
        _totalBps = total;
        emit RecipientsUpdated(list.length);
    }

    function splitToken(IERC20 token) external {
        uint256 balance = token.balanceOf(address(this));
        require(balance > 0, "FeeSplitter: empty");
        _payToken(token, balance);
        emit Distributed(address(token), balance);
    }

    function _splitNative(uint256 amount) private {
        if (amount == 0 || _totalBps == 0) return;
        for (uint256 i; i < _recipients.length; i++) {
            uint256 share = (amount * _recipients[i].bps) / 10_000;
            if (share > 0) {
                (bool ok,) = _recipients[i].account.call{value: share}("");
                require(ok, "FeeSplitter: native transfer failed");
            }
        }
    }

    function _payToken(IERC20 token, uint256 amount) private {
        for (uint256 i; i < _recipients.length; i++) {
            uint256 share = (amount * _recipients[i].bps) / 10_000;
            if (share > 0) {
                token.safeTransfer(_recipients[i].account, share);
            }
        }
    }
}
