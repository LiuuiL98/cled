"""Builds the app-specific QR pairing URI for the synthetic test channel."""
import ipaddress
import re
from urllib.parse import urlencode, urlunsplit


_TOKEN_RE = re.compile(r"^[a-f0-9]{64}$")


def build_pairing_uri(host: str, port: int, token: str) -> str:
    address = ipaddress.ip_address(host)
    if not isinstance(address, ipaddress.IPv4Address) or not address.is_private:
        raise ValueError("Pairing QR requires a private IPv4 address")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        raise ValueError("Token must be 64 lowercase hexadecimal characters")

    query = urlencode({"host": str(address), "port": str(port), "token": token})
    return urlunsplit(("guoshou-test", "pair", "", query, ""))
