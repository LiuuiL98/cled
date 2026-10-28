import base64
import json
import time
import unittest

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from otp_bridge import decode_otp_envelope


class OtpBridgeTests(unittest.TestCase):
    def make_envelope(self, code="123456", timestamp=None):
        key = AESGCM.generate_key(bit_length=256)
        nonce = b"0123456789ab"
        payload = {"code": code, "timestamp": timestamp or int(time.time())}
        ciphertext = AESGCM(key).encrypt(nonce, json.dumps(payload).encode(), None)
        envelope = {
            "nonce": base64.urlsafe_b64encode(nonce).decode().rstrip("="),
            "ciphertext": base64.urlsafe_b64encode(ciphertext).decode().rstrip("="),
        }
        return key, envelope

    def test_valid_code(self):
        key, envelope = self.make_envelope()
        self.assertEqual(decode_otp_envelope(key, envelope), "123456")

    def test_rejects_invalid_code(self):
        key, envelope = self.make_envelope("abc123")
        with self.assertRaises(Exception):
            decode_otp_envelope(key, envelope)

    def test_rejects_expired_code(self):
        key, envelope = self.make_envelope(timestamp=int(time.time()) - 1000)
        with self.assertRaises(Exception):
            decode_otp_envelope(key, envelope)


if __name__ == "__main__":
    unittest.main()
