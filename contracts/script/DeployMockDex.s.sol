// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {MockWETH} from "../src/mocks/MockWETH.sol";
import {MockUniswapV2Factory} from "../src/mocks/MockUniswapV2Factory.sol";
import {MockUniswapV2Router02} from "../src/mocks/MockUniswapV2Router02.sol";
import {StandardERC20} from "../src/fixtures/StandardERC20.sol";

/// @title Deploy the local mock DEX and seed a pair.
/// @notice Used to bring up an Anvil environment that mirrors the one the Python
///         end-to-end tests use:
///           forge script script/DeployMockDex.s.sol --rpc-url http://127.0.0.1:8545 --broadcast
contract DeployMockDex is Script {
    function run() external returns (address weth, address factory, address router, address token) {
        vm.startBroadcast();

        MockWETH wethC = new MockWETH();
        MockUniswapV2Factory factoryC = new MockUniswapV2Factory();
        MockUniswapV2Router02 routerC = new MockUniswapV2Router02(address(factoryC), address(wethC));
        StandardERC20 tokenC = new StandardERC20();

        tokenC.approve(address(routerC), 100_000 ether);
        routerC.addLiquidityETH{value: 100 ether}(
            address(tokenC), 100_000 ether, 0, 0, msg.sender, block.timestamp
        );

        vm.stopBroadcast();

        weth = address(wethC);
        factory = address(factoryC);
        router = address(routerC);
        token = address(tokenC);

        console2.log("WETH", weth);
        console2.log("Factory", factory);
        console2.log("Router", router);
        console2.log("Token", token);
    }
}
