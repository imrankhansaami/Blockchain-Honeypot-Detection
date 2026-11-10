"""Application settings loaded from the environment.

No secret is ever hardcoded. RPC endpoints and explorer API keys come from
environment variables; when an endpoint is missing the corresponding chain is
simply reported as unavailable rather than silently substituting a public URL.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AnalysisDepth = Literal["quick", "standard", "full"]


class Settings(BaseSettings):
    """Runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "Blockchain Honeypot Detection Tool"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # --- Database ---
    # Defaults to a local SQLite file so the app is runnable without Postgres.
    # Production deployments should point this at PostgreSQL.
    database_url: str = "sqlite+pysqlite:///./data/honeypot.db"
    db_echo: bool = False

    # --- RPC endpoints (per chain). Empty means "chain unavailable". ---
    mainnet_rpc_url: str = ""
    sepolia_rpc_url: str = ""
    bsc_rpc_url: str = ""
    bsc_testnet_rpc_url: str = ""

    # --- Explorer APIs ---
    etherscan_api_key: str = ""
    bscscan_api_key: str = ""

    # --- RPC hardening ---
    rpc_timeout_seconds: float = 20.0
    rpc_max_retries: int = 2
    # Only these hosts may ever be contacted over RPC. Guards against an
    # attacker-supplied RPC URL turning the analyzer into an SSRF proxy.
    rpc_allowed_hosts: list[str] = Field(default_factory=list)

    # --- Simulation ---
    anvil_binary: str = "anvil"
    fork_timeout_seconds: int = 120
    anvil_port_range_start: int = 8600
    anvil_port_range_end: int = 8700
    simulation_enabled: bool = True
    # Native amount used for the "small" scenario, in wei.
    sim_buy_amount_wei: int = 10**17  # 0.1 native

    # --- Reports ---
    report_output_dir: str = "./data/reports"

    # --- Rate limiting ---
    rate_limit_analyze: str = "20/minute"
    rate_limit_default: str = "120/minute"

    # --- Background tasks ---
    use_celery: bool = False
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- Static analysis ---
    slither_enabled: bool = False
    slither_binary: str = "slither"
    slither_timeout_seconds: int = 180

    @field_validator("rpc_allowed_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return [h.strip() for h in value.split(",") if h.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def _upper_level(cls, value: str) -> str:
        return value.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
