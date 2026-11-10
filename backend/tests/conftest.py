"""Shared pytest fixtures.

Anvil + fixture contracts are only required by the simulation tests; tests that
do not need a chain skip gracefully when Foundry artifacts are unavailable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make ``backend`` importable and put the Foundry binaries on PATH.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_foundry_bin = Path(os.environ.get("USERPROFILE", "")) / ".foundry" / "bin"
if _foundry_bin.exists():
    os.environ["PATH"] = str(_foundry_bin) + os.pathsep + os.environ.get("PATH", "")

from app.core.chains import ChainConfig, DexConfig  # noqa: E402
from app.simulations.artifacts import artifact_available  # noqa: E402

ARTIFACTS_READY = artifact_available("StandardERC20", "StandardERC20")


@pytest.fixture(scope="session")
def local_node():
    if not ARTIFACTS_READY:
        pytest.skip("Foundry artifacts missing - run 'forge build' in contracts/")
    from app.simulations.fork_manager import AnvilNode

    try:
        node = AnvilNode.start()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Anvil unavailable: {exc}")
    yield node
    node.destroy()


@pytest.fixture()
def dex(local_node):
    from tests.local_chain import deploy_dex

    return deploy_dex(local_node)


@pytest.fixture()
def mock_chain(local_node, dex):
    """A ChainConfig that points at the freshly deployed mock DEX."""
    return ChainConfig(
        chain_id=1,
        name="MockNet",
        short_name="mock",
        native_symbol="ETH",
        native_decimals=18,
        wrapped_native=dex["weth"].address,
        wrapped_native_symbol="WETH",
        dexes=(
            DexConfig(
                name="Mock DEX",
                factory=dex["factory"].address,
                router=dex["router"].address,
            ),
        ),
    )
