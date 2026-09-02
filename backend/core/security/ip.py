import ipaddress


def normalize_ip(raw: str) -> str:
    """Canonical IPv4/IPv6 string. Raises ValueError if not an address."""
    text = (raw or "").strip()
    if not text or text.lower() == "unknown":
        raise ValueError("invalid IP")
    return str(ipaddress.ip_address(text.split("%")[0]))
