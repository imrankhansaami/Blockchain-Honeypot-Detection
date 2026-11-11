// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC1155Receiver {
    function onERC1155Received(address operator, address from, uint256 id, uint256 value, bytes calldata data)
        external
        returns (bytes4);
}

/// @title Minimal ERC-1155 multi-token (reference implementation).
/// @notice Batch mint / transfer with owner-controlled supply per id.
contract ERC1155MultiToken {
    mapping(uint256 => mapping(address => uint256)) private _balances;
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    mapping(uint256 => uint256) public totalSupply;

    address public owner;
    string public uri;

    event TransferSingle(address indexed operator, address indexed from, address indexed to, uint256 id, uint256 value);
    event TransferBatch(
        address indexed operator,
        address indexed from,
        address indexed to,
        uint256[] ids,
        uint256[] values
    );
    event ApprovalForAll(address indexed account, address indexed operator, bool approved);

    modifier onlyOwner() {
        require(msg.sender == owner, "ERC1155MultiToken: not owner");
        _;
    }

    constructor(string memory uri_, address initialOwner) {
        uri = uri_;
        owner = initialOwner;
    }

    function setURI(string calldata newURI) external onlyOwner {
        uri = newURI;
    }

    function balanceOf(address account, uint256 id) public view returns (uint256) {
        return _balances[id][account];
    }

    function balanceOfBatch(address[] calldata accounts, uint256[] calldata ids)
        external
        view
        returns (uint256[] memory batch)
    {
        require(accounts.length == ids.length, "ERC1155MultiToken: length mismatch");
        batch = new uint256[](accounts.length);
        for (uint256 i; i < accounts.length; i++) {
            batch[i] = _balances[ids[i]][accounts[i]];
        }
    }

    function setApprovalForAll(address operator, bool approved) external {
        isApprovedForAll[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function mint(address to, uint256 id, uint256 amount) external onlyOwner {
        require(to != address(0), "ERC1155MultiToken: zero address");
        _balances[id][to] += amount;
        totalSupply[id] += amount;
        emit TransferSingle(msg.sender, address(0), to, id, amount);
    }

    function mintBatch(address to, uint256[] calldata ids, uint256[] calldata amounts) external onlyOwner {
        require(ids.length == amounts.length, "ERC1155MultiToken: length mismatch");
        for (uint256 i; i < ids.length; i++) {
            _balances[ids[i]][to] += amounts[i];
            totalSupply[ids[i]] += amounts[i];
            emit TransferSingle(msg.sender, address(0), to, ids[i], amounts[i]);
        }
    }

    function safeTransferFrom(address from, address to, uint256 id, uint256 amount, bytes calldata data) external {
        require(from == msg.sender || isApprovedForAll[from][msg.sender], "ERC1155MultiToken: not authorised");
        require(to != address(0), "ERC1155MultiToken: zero address");
        _balances[id][from] -= amount;
        _balances[id][to] += amount;
        emit TransferSingle(msg.sender, from, to, id, amount);
        _checkReceiver(msg.sender, from, to, id, amount, data);
    }

    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) external {
        require(ids.length == amounts.length, "ERC1155MultiToken: length mismatch");
        require(from == msg.sender || isApprovedForAll[from][msg.sender], "ERC1155MultiToken: not authorised");
        require(to != address(0), "ERC1155MultiToken: zero address");
        for (uint256 i; i < ids.length; i++) {
            _balances[ids[i]][from] -= amounts[i];
            _balances[ids[i]][to] += amounts[i];
        }
        emit TransferBatch(msg.sender, from, to, ids, amounts);
        if (to.code.length > 0) {
            require(
                IERC1155Receiver(to).onERC1155Received(msg.sender, from, ids[0], amounts[0], data)
                    == IERC1155Receiver.onERC1155Received.selector,
                "ERC1155MultiToken: unsafe recipient"
            );
        }
    }

    function _checkReceiver(
        address operator,
        address from,
        address to,
        uint256 id,
        uint256 amount,
        bytes calldata data
    ) private {
        if (to.code.length > 0) {
            require(
                IERC1155Receiver(to).onERC1155Received(operator, from, id, amount, data)
                    == IERC1155Receiver.onERC1155Received.selector,
                "ERC1155MultiToken: unsafe recipient"
            );
        }
    }
}
