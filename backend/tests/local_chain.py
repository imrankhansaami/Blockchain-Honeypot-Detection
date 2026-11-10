"""Helpers for deploying the Foundry fixtures onto a bare Anvil node."""

from __future__ import annotations

from web3 import Web3

from app.simulations.artifacts import load_artifact
from app.simulations.fork_manager import AnvilNode


def deploy(node: AnvilNode, source_file: str, contract: str, *args, deployer: str | None = None):
    w3 = node.w3
    abi, bytecode = load_artifact(source_file, contract)
    account = deployer or w3.eth.accounts[0]
    factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = factory.constructor(*args).transact({"from": account, "gas": 12_000_000})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return w3.eth.contract(address=receipt["contractAddress"], abi=abi)


def transact(node: AnvilNode, function_call, *, sender: str | None = None, value: int = 0):
    w3 = node.w3
    account = sender or w3.eth.accounts[0]
    tx_hash = function_call.transact({"from": account, "value": value, "gas": 12_000_000})
    return w3.eth.wait_for_transaction_receipt(tx_hash)


def call(node: AnvilNode, function_call):
    return function_call.call()


def deploy_dex(node: AnvilNode) -> dict:
    """Deploy the mock WETH/factory/router and return their addresses."""
    weth = deploy(node, "MockWETH", "MockWETH")
    factory = deploy(node, "MockUniswapV2Factory", "MockUniswapV2Factory")
    router = deploy(node, "MockUniswapV2Router02", "MockUniswapV2Router02", factory.address, weth.address)
    return {"weth": weth, "factory": factory, "router": router}


def add_liquidity_eth(node: AnvilNode, dex: dict, token, token_amount: int, eth_amount: int, *, owner: str | None = None):
    """Approve + add ETH liquidity for a token held by the deployer."""
    account = owner or node.w3.eth.accounts[0]
    token.functions.approve(dex["router"].address, token_amount).transact({"from": account, "gas": 1_000_000})
    dex["router"].functions.addLiquidityETH(
        token.address, token_amount, 0, 0, account, 2**32 - 1
    ).transact({"from": account, "value": eth_amount, "gas": 6_000_000})
    pair_addr = dex["factory"].functions.getPair(token.address, dex["weth"].address).call()
    return Web3.to_checksum_address(pair_addr)
