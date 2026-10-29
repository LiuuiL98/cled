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

PAIRING_PORT = 39173
PAIRING_KEY_NAME = "otp_bridge_aes_gcm_key_v1"


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


def _load_or_create_pairing_key() -> tuple[bytes, bool]:
    """Persist the LAN AES key in Windows Credential Manager when available."""
    try:
        from credential_store import load_secret, save_secret

        encoded = load_secret(PAIRING_KEY_NAME)
        if encoded:
            key = base64.urlsafe_b64decode(encoded + "===")
            if len(key) == 32:
                return key, True

        key = AESGCM.generate_key(bit_length=256)
        token = base64.urlsafe_b64encode(key).decode("ascii").rstrip("=")
        save_secret(PAIRING_KEY_NAME, token)
        return key, True
    except Exception:
        # A non-Windows/dev environment or unavailable Credential Manager
        # falls back to a fresh key. The QR then has to be scanned again.
        return AESGCM.generate_key(bit_length=256), False


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
    """LAN-only encrypted OTP receiver with a persistent pairing secret/port."""

    def __init__(self) -> None:
        self._key, self._persistent_key = _load_or_create_pairing_key()
        self._queue: queue.Queue[str] = queue.Queue()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._seen_nonces: set[str] = set()
        self._nonce_lock = threading.Lock()
        self._persistent_endpoint = False

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

        try:
            self._server = ThreadingHTTPServer(("0.0.0.0", PAIRING_PORT), Handler)
            self._persistent_endpoint = True
        except OSError:
            # An occupied fixed port is unusual; fall back to a temporary port.
            # The QR will show the new port, and the phone must re-pair once.
            self._server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
            self._persistent_endpoint = False

        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        token = base64.urlsafe_b64encode(self._key).decode("ascii").rstrip("=")
        return {
            "v": 1,
            "host": detect_lan_ip(),
            "port": self._server.server_address[1],
            "key": token,
            "persistent": bool(self._persistent_key and self._persistent_endpoint),
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
