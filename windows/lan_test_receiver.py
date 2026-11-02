"""LAN receiver for explicitly synthetic test messages only."""
from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable


TEST_SOURCE = "GUOSHOU_TEST_SIMULATOR"
TOKEN_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def load_or_create_token(path: Path | None = None) -> str:
    """Persist a random test-only token in the current Windows user's profile."""
    if path is None:
        profile = Path(os.environ.get("APPDATA") or Path.home())
        path = profile / "GuoshouCodeClipboard" / "test-token.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = path.read_text(encoding="ascii").strip()
        if TOKEN_PATTERN.fullmatch(existing):
            return existing
    except (OSError, UnicodeError):
        pass

    token = secrets.token_hex(32)
    path.write_text(token + "\n", encoding="ascii")
    return token


def validate_test_payload(raw: bytes, supplied_token: str, expected_token: str) -> str | None:
    if not hmac.compare_digest(supplied_token or "", expected_token):
        return None
    if len(raw) > 1024:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("source") != TEST_SOURCE:
        return None
    code = payload.get("code")
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    return code


def find_lan_ipv4() -> str:
    candidates: list[str] = []
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            ip = ipaddress.ip_address(address)
            if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                if address not in candidates:
                    candidates.append(address)
    except OSError:
        pass
    if candidates:
        return candidates[0]
    return "127.0.0.1"


class LanTestReceiver:
    def __init__(self, on_code: Callable[[str], None], port: int = 8765):
        self.token = load_or_create_token()
        self.on_code = on_code
        self.port = port
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                # Never log request bodies or OTP-like values.
                return

            def _reply(self, status: int, message: bytes):
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(message)))
                self.end_headers()
                self.wfile.write(message)

            def do_POST(self):
                if self.path != "/test-code":
                    self._reply(404, b"not found")
                    return
                if self.headers.get_content_type() != "application/json":
                    self._reply(415, b"json required")
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    self._reply(400, b"bad length")
                    return
                if length <= 0 or length > 1024:
                    self._reply(413, b"payload too large")
                    return
                raw = self.rfile.read(length)
                code = validate_test_payload(
                    raw,
                    self.headers.get("X-Test-Token", ""),
                    owner.token,
                )
                if code is None:
                    self._reply(403, b"rejected")
                    return
                owner.on_code(code)
                self._reply(200, b"accepted")

        self._server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
