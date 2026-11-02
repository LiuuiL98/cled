import unittest

from pairing_qr import build_pairing_uri


class PairingQrTests(unittest.TestCase):
    def test_builds_pairing_uri(self):
        uri = build_pairing_uri("192.168.1.20", 8765, "a" * 64)
        self.assertTrue(uri.startswith("guoshou-test://pair?"))
        self.assertIn("host=192.168.1.20", uri)
        self.assertIn("port=8765", uri)
        self.assertIn("token=" + "a" * 64, uri)

    def test_rejects_public_address(self):
        with self.assertRaises(ValueError):
            build_pairing_uri("8.8.8.8", 8765, "a" * 64)

    def test_rejects_invalid_token(self):
        with self.assertRaises(ValueError):
            build_pairing_uri("192.168.1.20", 8765, "token")


if __name__ == "__main__":
    unittest.main()
