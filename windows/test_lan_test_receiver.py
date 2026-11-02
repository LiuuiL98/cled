import json
import tempfile
import unittest
from pathlib import Path

from lan_test_receiver import (
    TEST_SOURCE,
    load_or_create_token,
    validate_test_payload,
)


class LanTestReceiverTests(unittest.TestCase):
    def setUp(self):
        self.token = "a" * 64

    def test_accepts_explicit_test_payload(self):
        raw = json.dumps({"source": TEST_SOURCE, "code": "693754"}).encode()
        self.assertEqual(validate_test_payload(raw, self.token, self.token), "693754")

    def test_rejects_wrong_token(self):
        raw = json.dumps({"source": TEST_SOURCE, "code": "693754"}).encode()
        self.assertIsNone(validate_test_payload(raw, "b" * 64, self.token))

    def test_rejects_non_test_source(self):
        raw = json.dumps({"source": "SMS_BROADCAST", "code": "693754"}).encode()
        self.assertIsNone(validate_test_payload(raw, self.token, self.token))

    def test_rejects_non_ascii_or_wrong_length(self):
        for value in ("12345", "1234567", "１２３４５６", "12ab56"):
            with self.subTest(value=value):
                raw = json.dumps({"source": TEST_SOURCE, "code": value}).encode()
                self.assertIsNone(validate_test_payload(raw, self.token, self.token))

    def test_token_is_persistent_between_starts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test-token.txt"
            first = load_or_create_token(path)
            second = load_or_create_token(path)
            self.assertEqual(first, second)
            self.assertRegex(first, r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
