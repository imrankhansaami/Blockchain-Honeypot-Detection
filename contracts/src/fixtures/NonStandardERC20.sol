// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Fixture 12 - Non-standard ERC-20: transfer/approve return nothing and
///        there is no symbol()/decimals() metadata.
/// @notice Used to verify the analyzer does not assume standard ERC-20 behavior
///         merely because the ABI contains familiar function names.
contract NonStandardERC20 {
    string public name = "Non Standard Token";
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor() {
        totalSupply = 1_000_000 ether;
        balanceOf[msg.sender] = totalSupply;
    }

    // NOTE: no return values, unlike ERC-20.
    function transfer(address to, uint256 value) external {
        require(balanceOf[msg.sender] >= value, "insufficient");
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
    }

    function transferFrom(address from, address to, uint256 value) external {
        require(balanceOf[from] >= value, "insufficient");
        require(allowance[from][msg.sender] >= value, "not allowed");
        allowance[from][msg.sender] -= value;
        balanceOf[from] -= value;
        balanceOf[to] += value;
        emit Transfer(from, to, value);
    }

    function approve(address spender, uint256 value) external {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
    }
}
