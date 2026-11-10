"""Load compiled Foundry artifacts for hermetic local simulation tests.

The compiled artifacts are produced by ``forge build`` in ``contracts/out``. They
are used to deploy the test fixtures onto a bare Anvil so the simulator can be
verified offline, without any external RPC.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("HONEYPOT_REPO_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3]


def contracts_out_dir() -> Path:
    return repo_root() / "contracts" / "out"


@lru_cache(maxsize=128)
def load_artifact(source_file: str, contract: str) -> tuple[list, str]:
    """Return (abi, bytecode) for ``contract`` in ``source_file``."""
    path = contracts_out_dir() / f"{source_file}.sol" / f"{contract}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Artifact not found: {path}. Run 'forge build' in the contracts directory."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    abi = data["abi"]
    bytecode = data["bytecode"]["object"]
    return abi, bytecode


def artifact_available(source_file: str, contract: str) -> bool:
    try:
        load_artifact(source_file, contract)
        return True
    except FileNotFoundError:
        return False
