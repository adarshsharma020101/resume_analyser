"""
Network egress guard.
Installs a socket-level hook that blocks all outbound connections
to non-local hosts when BLOCK_EXTERNAL_NETWORK=True.
This is the enforcement mechanism for the no-egress policy.
"""
from __future__ import annotations

import socket
from typing import Any

from .config import get_settings
from .logging import get_logger

log = get_logger(__name__)
settings = get_settings()

_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_ORIGINAL_CREATE_CONNECTION = socket.create_connection


def _is_local(host: str) -> bool:
    """Return True if the host is an allowed local/internal target."""
    if not host:
        return False
    h = host.lower().strip()
    # Loopback
    if h in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    # Docker-compose service names and configured allowed hosts
    if h in [a.lower() for a in settings.ALLOWED_HOSTS]:
        return True
    # 192.168.x.x, 10.x.x.x, 172.16-31.x.x
    if h.startswith(("192.168.", "10.", "172.")):
        return True
    return False


def _guarded_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
    if isinstance(host, str) and not _is_local(host):
        raise ConnectionRefusedError(
            f"[EGRESS BLOCKED] Outbound connection to '{host}' is prohibited. "
            "This application is local-only."
        )
    return _ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)


def _guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
    host = address[0] if address else ""
    if isinstance(host, str) and not _is_local(host):
        raise ConnectionRefusedError(
            f"[EGRESS BLOCKED] Outbound connection to '{host}' is prohibited."
        )
    return _ORIGINAL_CREATE_CONNECTION(address, *args, **kwargs)


def install_egress_guard() -> None:
    """Monkey-patch socket to block external connections."""
    if not settings.BLOCK_EXTERNAL_NETWORK:
        log.warning("Egress guard is DISABLED. External network access is allowed.")
        return
    socket.getaddrinfo = _guarded_getaddrinfo
    socket.create_connection = _guarded_create_connection
    log.info("Egress guard installed — only local/Docker-internal connections allowed.")


def uninstall_egress_guard() -> None:
    """Restore original socket functions (used in tests)."""
    socket.getaddrinfo = _ORIGINAL_GETADDRINFO
    socket.create_connection = _ORIGINAL_CREATE_CONNECTION
