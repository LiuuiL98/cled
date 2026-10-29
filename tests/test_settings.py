import json
import tempfile
import unittest
from pathlib import Path

from settings import DEFAULT_LOGIN_URL, Settings


class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        settings = Settings()
        self.assertEqual(settings.login_url, DEFAULT_LOGIN_URL)
        self.assertTrue(settings.keep_profile)
        self.assertTrue(settings.maximize_edge)
        self.assertFalse(settings.has_lock_position)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            expected = Settings(
                target_url="https://example.com/home",
                success_url_contains="/home",
                lock_x_ratio=0.782,
                lock_y_ratio=0.204,
                lock_maximize=True,
            )
            expected.save(path)
            actual = Settings.load(path)
            self.assertEqual(actual, expected)
            self.assertTrue(actual.has_lock_position)

    def test_rejects_invalid_saved_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(
                json.dumps({"lock_x_ratio": 1.5, "lock_y_ratio": 0.3}),
                encoding="utf-8",
            )
            actual = Settings.load(path)
            self.assertIsNone(actual.lock_x_ratio)
            self.assertIsNone(actual.lock_y_ratio)
            self.assertFalse(actual.has_lock_position)

    def test_invalid_file_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(Settings.load(path), Settings())


if __name__ == "__main__":
    unittest.main()
