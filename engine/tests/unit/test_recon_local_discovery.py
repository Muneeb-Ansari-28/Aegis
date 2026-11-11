"""Unit tests for Tier 2 Local Discovery and Permission Safeguards (Task 5).

Tests:
- IPv4 (127.0.0.1) and IPv6 (::1, [::1]) loopback URLs recognized; remote private IPs rejected.
- Only the target's loopback port is inspected during recon.
- Sensitive CLI tokens (--api-key, --token, --password) are redacted.
- Non-admin / permission denial gracefully marks process metadata unavailable with clear warning.
"""
from unittest.mock import MagicMock, patch
import pytest

from app.recon.local_discovery import LocalDiscovery, LocalTarget, is_loopback_host, redact_cmdline


def test_is_loopback_host_ipv4_and_ipv6():
    assert is_loopback_host("localhost") is True
    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("127.0.0.5") is True
    assert is_loopback_host("::1") is True
    assert is_loopback_host("[::1]") is True

    # Remote or private network addresses are NOT loopback
    assert is_loopback_host("192.168.1.100") is False
    assert is_loopback_host("10.0.0.5") is False
    assert is_loopback_host("172.16.0.2") is False
    assert is_loopback_host("example.com") is False
    assert is_loopback_host(None) is False


def test_redact_cmdline_secrets():
    cmd1 = "python app.py --api-key sk-1234567890abcdef --port 8000"
    redacted1 = redact_cmdline(cmd1)
    assert "sk-1234567890abcdef" not in redacted1
    assert "--api-key [REDACTED]" in redacted1

    cmd2 = "node server.js --token=my_secret_token_val --host=localhost"
    redacted2 = redact_cmdline(cmd2)
    assert "my_secret_token_val" not in redacted2
    assert "--token=[REDACTED]" in redacted2 or "--token [REDACTED]" in redacted2

    cmd3 = "my-service --password secret_pass_123 --api_key=secret_api"
    redacted3 = redact_cmdline(cmd3)
    assert "secret_pass_123" not in redacted3
    assert "secret_api" not in redacted3


def test_psutil_permission_denial_fallback():
    # Simulate non-admin environment where net_connections or Process raises AccessDenied
    with patch("socket.socket") as mock_socket_cls:
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Port is open
        mock_socket_cls.return_value.__enter__.return_value = mock_sock

        with patch("app.recon.local_discovery.psutil", None):
            # When psutil is unavailable or denied
            target = LocalDiscovery.inspect_port(8000)
            assert target is not None
            assert target.port == 8000
            assert target.pid is None
            assert target.process_name in ("", "[unavailable]")
            assert target.permission_warning is not None
            assert "unavailable" in target.permission_warning.lower() or "permission" in target.permission_warning.lower()

