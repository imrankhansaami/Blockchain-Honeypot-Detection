// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IFlashBorrower {
    function onFlashLoan(
        address initiator,
        address token,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external returns (bytes32);
}

/// @title ERC-3156-style flash loan provider.
/// @notice Lends the entire balance for the duration of one transaction and
///         requires repayment plus a fee. Included because flash-loan-funded
///         attacks are a core honeypot/rug vector the tool reasons about.
contract FlashLoanProvider is ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant CALLBACK_SUCCESS = keccak256("ERC3156FlashBorrower.onFlashLoan");

    IERC20 public immutable asset;
    uint256 public feeBps = 9; // 0.09%

    event FlashLoan(address indexed receiver, address indexed initiator, uint256 amount, uint256 fee);

    constructor(address _asset) {
        asset = IERC20(_asset);
    }

    function maxFlashLoan() external view returns (uint256) {
        return asset.balanceOf(address(this));
    }

    function flashFee(uint256 amount) public view returns (uint256) {
        return (amount * feeBps) / 10_000;
    }

    function setFeeBps(uint256 newFeeBps) external {
        require(newFeeBps <= 100, "FlashLoanProvider: fee too high");
        feeBps = newFeeBps;
    }

    function flashLoan(IFlashBorrower receiver, uint256 amount, bytes calldata data)
        external
        nonReentrant
        returns (bool)
    {
        uint256 balanceBefore = asset.balanceOf(address(this));
        require(amount <= balanceBefore, "FlashLoanProvider: amount exceeds balance");

        uint256 fee = flashFee(amount);
        asset.safeTransfer(address(receiver), amount);

        require(
            receiver.onFlashLoan(msg.sender, address(asset), amount, fee, data) == CALLBACK_SUCCESS,
            "FlashLoanProvider: callback failed"
        );

        asset.safeTransferFrom(address(receiver), address(this), amount + fee);
        require(
            asset.balanceOf(address(this)) >= balanceBefore + fee,
            "FlashLoanProvider: repayment shortfall"
        );
        emit FlashLoan(address(receiver), msg.sender, amount, fee);
        return true;
    }
}
