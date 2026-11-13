from fastapi import Request

from app.core.network import get_client_ip, is_ip_trusted


def _mock_request(client_host: str | None, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("latin-1")))

    scope = {
        "type": "http",
        "client": (client_host, 12345) if client_host is not None else None,
        "headers": headers,
    }
    return Request(scope)


def test_is_ip_trusted_handles_exact_and_cidr():
    trusted = ["127.0.0.1", "10.0.0.0/8", "192.168.1.50"]

    assert is_ip_trusted("127.0.0.1", trusted) is True
    assert is_ip_trusted("10.1.2.3", trusted) is True
    assert is_ip_trusted("10.254.254.254", trusted) is True
    assert is_ip_trusted("192.168.1.50", trusted) is True

    assert is_ip_trusted("192.168.1.51", trusted) is False
    assert is_ip_trusted("172.16.0.1", trusted) is False
    assert is_ip_trusted("invalid-ip", trusted) is False
    assert is_ip_trusted("", trusted) is False
    assert is_ip_trusted("127.0.0.1", []) is False


def test_direct_peer_without_trusted_proxies_ignores_forwarded_headers():
    # An attacker directly connects and supplies a fake X-Forwarded-For header
    req = _mock_request(client_host="203.0.113.195", forwarded_for="198.51.100.1")

    # With no trusted proxies configured, header MUST be ignored
    assert get_client_ip(req, trusted_proxies=[]) == "203.0.113.195"


def test_direct_peer_not_matching_trusted_proxies_ignores_forwarded_headers():
    # Trusted proxy is configured as 10.0.0.1, but caller is 198.51.100.5
    req = _mock_request(client_host="198.51.100.5", forwarded_for="203.0.113.10")

    assert get_client_ip(req, trusted_proxies=["10.0.0.1"]) == "198.51.100.5"


def test_trusted_proxy_resolves_forwarded_client_ip():
    # Legitimate reverse proxy at 10.0.0.1 forwards real client 203.0.113.42
    req = _mock_request(client_host="10.0.0.1", forwarded_for="203.0.113.42")

    assert get_client_ip(req, trusted_proxies=["10.0.0.1"]) == "203.0.113.42"


def test_chained_trusted_proxies_extracts_rightmost_untrusted_hop():
    # Client 203.0.113.42 -> Ingress 10.0.0.2 -> Reverse proxy 10.0.0.1 -> App
    # Client may have spoofed "1.2.3.4"
    # X-Forwarded-For becomes: "1.2.3.4, 203.0.113.42, 10.0.0.2"
    trusted = ["10.0.0.0/8"]
    req = _mock_request(
        client_host="10.0.0.1",
        forwarded_for="1.2.3.4, 203.0.113.42, 10.0.0.2",
    )

    # 10.0.0.1 is trusted. 10.0.0.2 is trusted.
    # 203.0.113.42 is the rightmost untrusted hop!
    # "1.2.3.4" spoofed by client is safely ignored!
    assert get_client_ip(req, trusted_proxies=trusted) == "203.0.113.42"


def test_malformed_forwarded_header_falls_back_safely():
    req = _mock_request(client_host="10.0.0.1", forwarded_for="garbage-not-an-ip")
    assert get_client_ip(req, trusted_proxies=["10.0.0.1"]) == "10.0.0.1"


def test_unknown_client_host_returns_unknown():
    req = _mock_request(client_host=None, forwarded_for="1.2.3.4")
    assert get_client_ip(req, trusted_proxies=["10.0.0.1"]) == "unknown"
