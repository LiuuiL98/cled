import unittest

from code_matcher import is_valid_code


class CodeMatcherTests(unittest.TestCase):
    def test_accepts_six_ascii_digits(self):
        self.assertTrue(is_valid_code("693754"))

    def test_rejects_wrong_length_and_non_digits(self):
        for value in ("", "12345", "1234567", "12a456", "１２３４５６"):
            with self.subTest(value=value):
                self.assertFalse(is_valid_code(value))


if __name__ == "__main__":
    unittest.main()
