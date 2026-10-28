from __future__ import annotations

import base64
import json
import queue
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def detect_lan_ip() -> str:
    """Return the IPv4 address used for the default route without sending data."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        address = sock.getsockname()[0]
        if address and not address.startswith("127."):
            return address
    except OSError:
        pass
    finally:
        sock.close()
    return "127.0.0.1"


def decode_otp_envelope(key: bytes, envelope: dict) -> str:
    nonce = base64.urlsafe_b64decode(envelope["nonce"] + "===")
    ciphertext = base64.urlsafe_b64decode(envelope["ciphertext"] + "===")
    if len(nonce) != 12 or len(ciphertext) > 2048:
        raise ValueError("invalid envelope size")
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    payload = json.loads(plaintext.decode("utf-8"))
    timestamp = int(payload.get("timestamp", 0))
    if abs(int(time.time()) - timestamp) > 120:
        raise ValueError("expired message")
    code = str(payload.get("code", ""))
    if not re.fullmatch(r"[0-9]{4,8}", code):
        raise ValueError("invalid code")
    return code


class OTPBridge:
    """LAN-only encrypted OTP receiver. A fresh key is generated each launch."""

    def __init__(self) -> None:
        self._key = AESGCM.generate_key(bit_length=256)
        self._queue: queue.Queue[str] = queue.Queue()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._seen_nonces: set[str] = set()
        self._nonce_lock = threading.Lock()

    def start(self) -> dict:
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:
                # Never log message bodies or authentication codes.
                return

            def _respond(self, status: int, body: dict) -> None:
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self) -> None:
                if self.path != "/otp":
                    self._respond(404, {"ok": False})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 4096:
                        raise ValueError("invalid request size")
                    envelope = json.loads(self.rfile.read(length).decode("utf-8"))
                    nonce_key = str(envelope.get("nonce", ""))
                    with bridge._nonce_lock:
                        if nonce_key in bridge._seen_nonces:
                            raise ValueError("replayed message")
                    code = decode_otp_envelope(bridge._key, envelope)
                    with bridge._nonce_lock:
                        bridge._seen_nonces.add(nonce_key)
                        if len(bridge._seen_nonces) > 256:
                            bridge._seen_nonces.clear()
                            bridge._seen_nonces.add(nonce_key)
                    bridge._queue.put(code)
                    self._respond(200, {"ok": True})
                except Exception:
                    self._respond(400, {"ok": False, "error": "invalid or expired code"})

        self._server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        token = base64.urlsafe_b64encode(self._key).decode("ascii").rstrip("=")
        return {
            "v": 1,
            "host": detect_lan_ip(),
            "port": self._server.server_address[1],
            "key": token,
        }

    def get_latest_code(self) -> Optional[str]:
        latest = None
        while True:
            try:
                latest = self._queue.get_nowait()
            except queue.Empty:
                return latest

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        self._thread = None
        self._key = b"\x00" * len(self._key)
