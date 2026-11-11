// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IBuybackRouter {
    function swapExactETHForTokens(uint256 amountOutMin, address[] calldata path, address to, uint256 deadline)
        external
        payable
        returns (uint256[] memory);
}

/// @title Token buyback & burn.
/// @notice The owner funds the contract with ETH and triggers a market buy which
///         is then burned. Combines a privileged trigger with an irreversible
///         supply reduction.
contract TokenBuyback is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable token;
    IBuybackRouter public router;
    address public weth;

    uint256 public totalBought;
    uint256 public totalBurned;

    event Buyback(uint256 ethSpent, uint256 tokensBought);
    event RouterUpdated(address indexed router, address indexed weth);

    constructor(address _token, address _router, address _weth) Ownable(msg.sender) {
        token = IERC20(_token);
        router = IBuybackRouter(_router);
        weth = _weth;
    }

    receive() external payable {}

    function setRouter(address _router, address _weth) external onlyOwner {
        router = IBuybackRouter(_router);
        weth = _weth;
        emit RouterUpdated(_router, _weth);
    }

    /// @notice Spend `ethAmount` of this contract's balance buying and burning tokens.
    function buybackAndBurn(uint256 ethAmount, uint256 amountOutMin) external onlyOwner nonReentrant {
        require(ethAmount <= address(this).balance, "TokenBuyback: insufficient balance");
        address[] memory path = new address[](2);
        path[0] = weth;
        path[1] = address(token);

        uint256 before = token.balanceOf(address(this));
        router.swapExactETHForTokens{value: ethAmount}(amountOutMin, path, address(this), block.timestamp);
        uint256 bought = token.balanceOf(address(this)) - before;

        token.safeTransfer(address(0xdead), bought);
        totalBought += bought;
        totalBurned += bought;
        emit Buyback(ethAmount, bought);
    }

    function recoverToken(IERC20 other, uint256 amount) external onlyOwner {
        require(address(other) != address(token), "TokenBuyback: cannot recover buyback token");
        other.safeTransfer(owner(), amount);
    }
}
