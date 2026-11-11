// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title Fixture 14 - Rebase token.
/// @notice Balances are stored as *shares*; a public multiplier converts shares
///         to token amounts. The owner can change the multiplier, rebasing every
///         balance without moving tokens. Holders are diluted or expanded.
/// @dev Used to verify the analyzer flags owner-controlled supply manipulation
///      that is not visible through `totalSupply()` changes alone.
contract RebaseToken is ERC20, Ownable {
    uint256 private constant PRECISION = 1e18;

    uint256 private _sharesTotal;
    mapping(address => uint256) private _shares;
    uint256 private _multiplier = PRECISION;

    event Rebase(uint256 oldMultiplier, uint256 newMultiplier);

    constructor() ERC20("Rebase Token", "RBASE") Ownable(msg.sender) {
        _mintShares(msg.sender, 1_000_000 ether);
    }

    function multiplier() external view returns (uint256) {
        return _multiplier;
    }

    /// @notice Owner-controlled rebase. Arbitrary multiplier changes dilute or
    ///         inflate every holder with a single transaction.
    function rebase(uint256 newMultiplier) external onlyOwner {
        require(newMultiplier > 0, "RebaseToken: zero multiplier");
        uint256 old = _multiplier;
        _multiplier = newMultiplier;
        emit Rebase(old, newMultiplier);
    }

    function totalSupply() public view override returns (uint256) {
        return (_sharesTotal * _multiplier) / PRECISION;
    }

    function balanceOf(address account) public view override returns (uint256) {
        return (_shares[account] * _multiplier) / PRECISION;
    }

    function sharesOf(address account) external view returns (uint256) {
        return _shares[account];
    }

    function _mintShares(address to, uint256 value) private {
        uint256 shares = (value * PRECISION) / _multiplier;
        _shares[to] += shares;
        _sharesTotal += shares;
        emit Transfer(address(0), to, value);
    }

    function _update(address from, address to, uint256 value) internal override {
        uint256 shares = (value * PRECISION) / _multiplier;
        if (from == address(0)) {
            _sharesTotal += shares;
        } else {
            require(_shares[from] >= shares, "RebaseToken: insufficient shares");
            _shares[from] -= shares;
        }
        if (to == address(0)) {
            _sharesTotal -= shares;
        } else {
            _shares[to] += shares;
        }
        emit Transfer(from, to, value);
    }
}
