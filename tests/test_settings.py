import tempfile
import unittest
from pathlib import Path

from settings import DEFAULT_LOGIN_URL, Settings


class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        settings = Settings()
        self.assertEqual(settings.login_url, DEFAULT_LOGIN_URL)
        self.assertTrue(settings.keep_profile)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            expected = Settings(target_url="https://example.com/home", success_url_contains="/home")
            expected.save(path)
            actual = Settings.load(path)
            self.assertEqual(actual, expected)

    def test_invalid_file_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(Settings.load(path), Settings())


if __name__ == "__main__":
    unittest.main()
