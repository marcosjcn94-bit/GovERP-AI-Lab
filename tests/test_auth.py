import unittest

from gov_erp.auth import create_session_token, verify_session_token


class SessionTokenTest(unittest.TestCase):
    SECRET = "secret-key-that-is-at-least-32-bytes"

    def test_signed_token_carries_the_server_approved_tenant(self):
        token = create_session_token("user-1", "4106902", self.SECRET, now=1000)
        claims = verify_session_token(token, self.SECRET, now=1001)
        self.assertEqual(claims.user_id, "user-1")
        self.assertEqual(claims.municipality_id, "4106902")

    def test_rejects_tampered_and_expired_tokens(self):
        token = create_session_token("user-1", "4106902", self.SECRET, now=1000)
        with self.assertRaises(ValueError):
            verify_session_token(token + "x", self.SECRET, now=1001)
        with self.assertRaises(ValueError):
            verify_session_token(token, self.SECRET, now=4600)
