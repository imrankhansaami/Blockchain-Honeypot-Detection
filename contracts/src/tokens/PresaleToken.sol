// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Fixture 17 - Presale token.
/// @notice Multi-role presale token with a trading switch, max-wallet limit and
///         separate buy/sell taxes. Combines several independent privileges to
///         exercise correlated-finding de-duplication in the risk engine.
contract PresaleToken is ERC20, AccessControl {
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");
    bytes32 public constant FEE_MANAGER_ROLE = keccak256("FEE_MANAGER_ROLE");

    address public pair;
    address public treasury;
    address public presaleWallet;

    bool public tradingEnabled;
    uint256 public maxWalletBps = 200; // 2% of supply
    uint256 public buyTaxBps;
    uint256 public sellTaxBps;

    mapping(address => bool) public isTaxExempt;
    uint256 public launchBlock;

    event TradingEnabled(uint256 launchBlock);
    event TaxesUpdated(uint256 buyTaxBps, uint256 sellTaxBps);

    constructor(address _treasury, address _presaleWallet) ERC20("Presale Token", "PRE") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(OPERATOR_ROLE, msg.sender);
        _grantRole(FEE_MANAGER_ROLE, msg.sender);
        treasury = _treasury;
        presaleWallet = _presaleWallet;
        isTaxExempt[msg.sender] = true;
        isTaxExempt[_treasury] = true;
        _mint(_presaleWallet, 600_000 ether);
        _mint(msg.sender, 400_000 ether);
    }

    function setPair(address _pair) external onlyRole(OPERATOR_ROLE) {
        pair = _pair;
    }

    function enableTrading() external onlyRole(OPERATOR_ROLE) {
        tradingEnabled = true;
        launchBlock = block.number;
        emit TradingEnabled(block.number);
    }

    function setTaxes(uint256 _buyTaxBps, uint256 _sellTaxBps) external onlyRole(FEE_MANAGER_ROLE) {
        require(_buyTaxBps <= 2000 && _sellTaxBps <= 2000, "PresaleToken: tax too high");
        buyTaxBps = _buyTaxBps;
        sellTaxBps = _sellTaxBps;
        emit TaxesUpdated(_buyTaxBps, _sellTaxBps);
    }

    function setMaxWalletBps(uint256 bps) external onlyRole(OPERATOR_ROLE) {
        maxWalletBps = bps;
    }

    function setTaxExempt(address account, bool exempt) external onlyRole(FEE_MANAGER_ROLE) {
        isTaxExempt[account] = exempt;
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            require(tradingEnabled, "PresaleToken: trading disabled");
            if (pair != address(0) && !isTaxExempt[to] && to != pair) {
                require(value + balanceOf(to) <= (totalSupply() * maxWalletBps) / 10_000, "PresaleToken: max wallet");
            }
            uint256 fee;
            if (pair != address(0) && !isTaxExempt[from]) {
                if (from == pair) {
                    fee = (value * buyTaxBps) / 10_000;
                } else if (to == pair) {
                    fee = (value * sellTaxBps) / 10_000;
                }
            }
            if (fee > 0) {
                super._update(from, treasury, fee);
            }
            super._update(from, to, value - fee);
        } else {
            super._update(from, to, value);
        }
    }
}
