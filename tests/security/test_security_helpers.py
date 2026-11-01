import unittest

from utils.security import configured_secret, secret_matches


class TestSecurityHelpers(unittest.TestCase):
    def test_missing_secret_never_authenticates(self):
        self.assertFalse(secret_matches("anything", ""))
        self.assertFalse(secret_matches("", "configured-secret"))

    def test_secret_comparison_accepts_only_exact_value(self):
        self.assertTrue(secret_matches("correct-secret", "correct-secret"))
        self.assertFalse(secret_matches("wrong-secret", "correct-secret"))


if __name__ == "__main__":
    unittest.main()
