import ipaddress
import logging

from fastapi import Request

logger = logging.getLogger(__name__)


def is_ip_trusted(ip_str: str, trusted_proxies: list[str]) -> bool:
    if not ip_str or not trusted_proxies:
        return False
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False

    for trusted in trusted_proxies:
        trusted_clean = trusted.strip()
        if not trusted_clean:
            continue
        try:
            if "/" in trusted_clean:
                if addr in ipaddress.ip_network(trusted_clean, strict=False):
                    return True
            else:
                if addr == ipaddress.ip_address(trusted_clean):
                    return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request, trusted_proxies: list[str]) -> str:
    peer_ip = request.client.host if request.client else "unknown"
    if peer_ip == "unknown":
        return "unknown"

    if not trusted_proxies or not is_ip_trusted(peer_ip, trusted_proxies):
        # Peer is not a configured trusted proxy; ignore forwarded headers to prevent spoofing
        return peer_ip

    forwarded_header = request.headers.get("X-Forwarded-For")
    if not forwarded_header:
        return peer_ip

    hops = [h.strip() for h in forwarded_header.split(",") if h.strip()]
    if not hops:
        return peer_ip

    # Walk backwards from the rightmost hop (the one closest to our trusted proxy)
    for hop in reversed(hops):
        try:
            addr = ipaddress.ip_address(hop)
        except ValueError:
            continue
        if not is_ip_trusted(str(addr), trusted_proxies):
            return str(addr)

    # If all hops were trusted, fallback to leftmost valid hop or peer_ip
    try:
        return str(ipaddress.ip_address(hops[0]))
    except ValueError:
        return peer_ip
