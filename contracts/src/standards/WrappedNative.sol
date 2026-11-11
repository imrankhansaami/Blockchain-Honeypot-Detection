// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title Canonical wrapped-native token (WETH/WBNB pattern).
/// @notice Reference implementation used by the analyzer to recognise wrapped
///         native tokens and their deposit/withdraw interface.
contract WrappedNative is ERC20 {
    event Deposit(address indexed dst, uint256 wad);
    event Withdrawal(address indexed src, uint256 wad);

    constructor(string memory name_, string memory symbol_) ERC20(name_, symbol_) {}

    receive() external payable {
        deposit();
    }

    function deposit() public payable {
        _mint(msg.sender, msg.value);
        emit Deposit(msg.sender, msg.value);
    }

    function withdraw(uint256 wad) external {
        require(balanceOf(msg.sender) >= wad, "WrappedNative: balance");
        _burn(msg.sender, wad);
        (bool ok,) = msg.sender.call{value: wad}("");
        require(ok, "WrappedNative: transfer failed");
        emit Withdrawal(msg.sender, wad);
    }

    function totalSupply() public view override returns (uint256) {
        return address(this).balance;
    }
}
