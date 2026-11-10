"""Anvil process management.

Each analysis runs in its own throwaway Anvil instance bound to a free local
port. Instances are always torn down. Two modes are supported:

  * ``fork``  - Anvil forks a real chain at a specific block (the production
    simulation path);
  * ``local`` - a bare Anvil with no fork, used to deploy the Foundry test
    fixtures for hermetic, offline verification of the simulator.

No private key is ever required: test wallets are funded and impersonated via
``anvil_*`` RPC methods, so simulations never touch real funds or keys.
"""

from __future__ import annotations

import socket
import subprocess
import time
from dataclasses import dataclass, field

from web3 import Web3

from app.core.config import get_settings
from app.core.exceptions import SimulationError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _free_port(start: int, end: int) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SimulationError("No free port available for Anvil")


@dataclass
class AnvilNode:
    process: subprocess.Popen
    port: int
    w3: Web3
    fork_url: str | None = None
    fork_block: int | None = None
    chain_id: int | None = None
    _log_path: str | None = field(default=None, repr=False)

    @property
    def rpc_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    # --- lifecycle ----------------------------------------------------------

    @classmethod
    def start(
        cls,
        *,
        fork_url: str | None = None,
        fork_block: int | None = None,
        chain_id: int | None = None,
        timeout: int | None = None,
    ) -> "AnvilNode":
        settings = get_settings()
        timeout = timeout or settings.fork_timeout_seconds
        port = _free_port(settings.anvil_port_range_start, settings.anvil_port_range_end)

        args = [
            settings.anvil_binary,
            "--port",
            str(port),
            "--host",
            "127.0.0.1",
            "--silent",
        ]
        if chain_id is not None:
            args += ["--chain-id", str(chain_id)]
        if fork_url:
            args += ["--fork-url", fork_url]
            if fork_block is not None:
                args += ["--fork-block-number", str(fork_block)]

        logger.info("Starting Anvil on port %s (fork=%s)", port, bool(fork_url))
        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except FileNotFoundError as exc:
            raise SimulationError(
                f"Anvil binary '{settings.anvil_binary}' not found. Install Foundry."
            ) from exc

        w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{port}", request_kwargs={"timeout": 10}))
        deadline = time.time() + timeout
        ready = False
        while time.time() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise SimulationError(f"Anvil exited early: {output[:500]}")
            try:
                if w3.is_connected():
                    w3.eth.chain_id
                    ready = True
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.2)

        if not ready:
            process.kill()
            raise SimulationError(f"Anvil did not become ready within {timeout}s")

        return cls(
            process=process,
            port=port,
            w3=w3,
            fork_url=fork_url,
            fork_block=fork_block,
            chain_id=chain_id,
        )

    def destroy(self) -> None:
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to stop Anvil cleanly: %s", exc)
        finally:
            if self.process.stdout:
                try:
                    self.process.stdout.close()
                except Exception:  # noqa: BLE001
                    pass

    def __enter__(self) -> "AnvilNode":
        return self

    def __exit__(self, *exc: object) -> None:
        self.destroy()

    # --- anvil_ RPC helpers -------------------------------------------------

    def set_balance(self, address: str, wei: int) -> None:
        addr = Web3.to_checksum_address(address)
        self.w3.provider.make_request("anvil_setBalance", [addr, hex(wei)])

    def impersonate(self, address: str) -> None:
        addr = Web3.to_checksum_address(address)
        self.w3.provider.make_request("anvil_impersonateAccount", [addr])

    def stop_impersonating(self, address: str) -> None:
        addr = Web3.to_checksum_address(address)
        self.w3.provider.make_request("anvil_stopImpersonatingAccount", [addr])

    def mine(self) -> None:
        self.w3.provider.make_request("anvil_mine", [])

    def current_block(self) -> int:
        return int(self.w3.eth.block_number)
