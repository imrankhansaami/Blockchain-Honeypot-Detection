"""API validation and endpoint tests (no external RPC required)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "disclaimer" in resp.json()


def test_health_lists_chains(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    chain_ids = {c["chain_id"] for c in body["chains"]}
    assert 1 in chain_ids and 56 in chain_ids


def test_chains_endpoint(client):
    resp = client.get("/api/v1/chains")
    assert resp.status_code == 200
    chains = resp.json()
    assert any(c["wrapped_native"] for c in chains)


def test_analyze_rejects_bad_address(client):
    resp = client.post(
        "/api/v1/analyze",
        json={"chain_id": 1, "token_address": "not-an-address", "analysis_depth": "standard"},
    )
    assert resp.status_code == 422


def test_analyze_rejects_unsupported_chain(client):
    resp = client.post(
        "/api/v1/analyze",
        json={
            "chain_id": 999999,
            "token_address": "0x0000000000000000000000000000000000000001",
            "analysis_depth": "standard",
        },
    )
    assert resp.status_code == 400


def test_analyze_returns_queued(client):
    resp = client.post(
        "/api/v1/analyze",
        json={
            "chain_id": 1,
            "token_address": "0x0000000000000000000000000000000000000001",
            "analysis_depth": "quick",
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["analysis_id"]


def test_missing_analysis_returns_404(client):
    resp = client.get("/api/v1/analyze/does-not-exist")
    assert resp.status_code == 404


def test_stats_endpoint(client):
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 200
    assert "total_analyses" in resp.json()
