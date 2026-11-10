"""Simulation schemas shared by the simulator, API and report generator."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TxResult(BaseModel):
    success: bool
    gas_used: int | None = None
    error: str | None = None
    revert_reason: str | None = None
    tx_hash: str | None = None
    decoded_log_count: int = 0


class ScenarioResult(BaseModel):
    name: str
    wallet: str
    fork_block: int
    buy_amount_wei: int
    expected_tokens_out: int | None = None
    tokens_received: int | None = None
    buy_tax_bps: float | None = None
    buy_result: TxResult
    sell_amount_tokens: int | None = None
    expected_native_out: int | None = None
    native_received_wei: int | None = None
    sell_tax_bps: float | None = None
    sell_result: TxResult | None = None
    gas_price_wei: int | None = None
    notes: list[str] = Field(default_factory=list)


class SimulationReport(BaseModel):
    performed: bool = False
    reason: str | None = None
    fork_block: int | None = None
    chain_id: int
    token_address: str
    pair: dict | None = None
    router: str | None = None
    factory: str | None = None
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    buy_success_any: bool = False
    sell_success_any: bool = False
    buy_tax_bps: float | None = None
    sell_tax_bps: float | None = None
    can_buy_cannot_sell: bool = False
    limitations: list[str] = Field(default_factory=list)
