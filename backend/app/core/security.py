"""Security helpers: SSRF protection and safe RPC endpoint validation."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.exceptions import SSRFBlockedError

_ALLOWED_SCHEMES = {"http", "https"}


def _is_private_host(host: str) -> bool:
    if host in {"localhost", "localhost.localdomain"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def validate_rpc_url(url: str, *, allow_private: bool = False) -> str:
    """Validate an RPC endpoint URL and block SSRF targets.

    Rules:
      * scheme must be http(s);
      * if ``rpc_allowed_hosts`` is configured, the host MUST be listed;
      * private / loopback / link-local addresses are rejected unless
        ``allow_private`` is set (local Anvil uses this internally).
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise SSRFBlockedError(f"RPC URL scheme '{parsed.scheme}' is not allowed")
    if not parsed.hostname:
        raise SSRFBlockedError("RPC URL is missing a host")

    host = parsed.hostname.lower()
    allowlist = [h.lower() for h in get_settings().rpc_allowed_hosts]
    if allowlist and host not in allowlist:
        raise SSRFBlockedError(
            f"RPC host '{host}' is not in the configured allow-list"
        )
    if not allow_private and _is_private_host(host):
        raise SSRFBlockedError(
            f"RPC host '{host}' resolves to a private address and is blocked"
        )
    return url
