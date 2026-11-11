// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Minimal multi-signature wallet.
/// @notice Frequently used as the owner of a token contract so that no single
///         key can abuse owner privileges. The analyzer should recognise this as
///         a mitigating control rather than a red flag.
contract MultiSigWallet {
    event OwnerSet(address indexed owner, bool enabled);
    event Submission(uint256 indexed txId);
    event Confirmation(address indexed sender, uint256 indexed txId);
    event Revocation(address indexed sender, uint256 indexed txId);
    event Execution(uint256 indexed txId, address indexed to, uint256 value, bytes data);
    event ExecutionFailure(uint256 indexed txId);
    event Deposit(address indexed sender, uint256 value);

    struct Transaction {
        address to;
        uint256 value;
        bytes data;
        bool executed;
        uint256 confirmations;
    }

    mapping(address => bool) public isOwner;
    mapping(uint256 => mapping(address => bool)) public confirmedBy;
    mapping(uint256 => Transaction) private _transactions;

    address[] public owners;
    uint256 public required;
    uint256 public transactionCount;

    modifier onlyOwner() {
        require(isOwner[msg.sender], "MultiSigWallet: not owner");
        _;
    }

    modifier notExecuted(uint256 txId) {
        require(!_transactions[txId].executed, "MultiSigWallet: executed");
        _;
    }

    constructor(address[] memory _owners, uint256 _required) {
        require(_owners.length > 0, "MultiSigWallet: no owners");
        require(_required > 0 && _required <= _owners.length, "MultiSigWallet: bad threshold");
        for (uint256 i; i < _owners.length; i++) {
            address owner = _owners[i];
            require(owner != address(0) && !isOwner[owner], "MultiSigWallet: invalid owner");
            isOwner[owner] = true;
            owners.push(owner);
            emit OwnerSet(owner, true);
        }
        required = _required;
    }

    receive() external payable {
        emit Deposit(msg.sender, msg.value);
    }

    function submit(address to, uint256 value, bytes calldata data) external onlyOwner returns (uint256 txId) {
        txId = transactionCount;
        _transactions[txId] = Transaction({to: to, value: value, data: data, executed: false, confirmations: 0});
        transactionCount += 1;
        emit Submission(txId);
    }

    function confirm(uint256 txId) public onlyOwner notExecuted(txId) {
        require(!confirmedBy[txId][msg.sender], "MultiSigWallet: already confirmed");
        confirmedBy[txId][msg.sender] = true;
        _transactions[txId].confirmations += 1;
        emit Confirmation(msg.sender, txId);
    }

    function revoke(uint256 txId) external onlyOwner notExecuted(txId) {
        require(confirmedBy[txId][msg.sender], "MultiSigWallet: not confirmed");
        confirmedBy[txId][msg.sender] = false;
        _transactions[txId].confirmations -= 1;
        emit Revocation(msg.sender, txId);
    }

    function execute(uint256 txId) external onlyOwner notExecuted(txId) {
        Transaction storage txn = _transactions[txId];
        require(txn.confirmations >= required, "MultiSigWallet: not enough confirmations");
        txn.executed = true;
        (bool ok,) = txn.to.call{value: txn.value}(txn.data);
        if (ok) {
            emit Execution(txId, txn.to, txn.value, txn.data);
        } else {
            txn.executed = false;
            emit ExecutionFailure(txId);
        }
    }

    function getTransaction(uint256 txId)
        external
        view
        returns (address to, uint256 value, bytes memory data, bool executed, uint256 confirmations)
    {
        Transaction storage txn = _transactions[txId];
        return (txn.to, txn.value, txn.data, txn.executed, txn.confirmations);
    }
}
