"""SSRF / RPC endpoint validation tests."""

from __future__ import annotations

import pytest

from app.core.exceptions import SSRFBlockedError
from app.core.security import validate_rpc_url


def test_rejects_private_ip():
    with pytest.raises(SSRFBlockedError):
        validate_rpc_url("http://127.0.0.1:8545")


def test_rejects_link_local():
    with pytest.raises(SSRFBlockedError):
        validate_rpc_url("http://169.254.169.254/latest/meta-data")


def test_rejects_non_http_scheme():
    with pytest.raises(SSRFBlockedError):
        validate_rpc_url("file:///etc/passwd")


def test_allows_public_https():
    assert validate_rpc_url("https://mainnet.example.com") == "https://mainnet.example.com"


def test_allows_private_when_explicitly_permitted():
    assert validate_rpc_url("http://127.0.0.1:8545", allow_private=True)


def test_allowlist_enforced(monkeypatch):
    from app.core import security

    settings = security.get_settings()
    monkeypatch.setattr(settings, "rpc_allowed_hosts", ["allowed.example.com"], raising=False)
    with pytest.raises(SSRFBlockedError):
        validate_rpc_url("https://evil.example.com")
    assert validate_rpc_url("https://allowed.example.com") == "https://allowed.example.com"
