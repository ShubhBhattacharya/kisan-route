"""Comprehensive Test Suite for Module 23 - Private Owner Control & Access Management."""

import unittest
from app import create_app


class TestModule23OwnerControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_01_unauthenticated_owner_route_denied(self):
        """Unauthenticated visitor cannot access /owner/guardian/."""
        client = self.app.test_client()
        res = client.get("/owner/guardian/")
        self.assertEqual(res.status_code, 401)
        self.assertIn(b"Owner Control Center", res.data)

    def test_02_normal_customer_role_forbidden(self):
        """Normal customer session attempting to access /owner/guardian/ receives 403 Forbidden."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "customer"
            sess["name"] = "Demo Customer"
            sess["is_owner_authenticated"] = True  # Attempted privilege escalation
        res = client.get("/owner/guardian/")
        self.assertEqual(res.status_code, 403)

    def test_03_normal_farmer_role_forbidden(self):
        """Normal farmer session attempting to access /owner/guardian/ receives 403 Forbidden."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["role"] = "farmer"
            sess["name"] = "Demo Farmer"
            sess["is_owner_authenticated"] = True
        res = client.get("/owner/guardian/")
        self.assertEqual(res.status_code, 403)

    def test_04_normal_driver_and_wholesaler_forbidden(self):
        """Normal driver and wholesaler sessions cannot access owner routes."""
        for role, uid in [("driver", 3), ("wholesaler", 4), ("cluster", 5)]:
            client = self.app.test_client()
            with client.session_transaction() as sess:
                sess["user_id"] = uid
                sess["role"] = role
                sess["is_owner_authenticated"] = True
            res = client.get("/owner/guardian/")
            self.assertEqual(res.status_code, 403)

    def test_05_authenticated_owner_full_visibility(self):
        """Authenticated Owner accesses dashboard and sees telemetry, synthetic probes, and logs."""
        client = self.app.test_client()
        res_login = client.post("/owner/guardian/", data={"owner_pin": "123456"}, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"KisanRoute Guardian \xe2\x80\x94 Owner Control Center", res_login.data)
        self.assertIn(b"Synthetic User Workflow Verification", res_login.data)
        self.assertIn(b"Private Real-Time Audit Telemetry", res_login.data)

    def test_06_owner_actions_pause_and_resume(self):
        """Owner can pause and resume the Guardian AI sentinel."""
        client = self.app.test_client()
        client.post("/owner/guardian/", data={"owner_pin": "123456"})
        
        # Pause
        res_pause = client.post("/owner/guardian/action/pause", follow_redirects=True)
        self.assertEqual(res_pause.status_code, 200)
        self.assertIn(b"Guardian AI has been PAUSED", res_pause.data)

        # Resume
        res_resume = client.post("/owner/guardian/action/resume", follow_redirects=True)
        self.assertEqual(res_resume.status_code, 200)
        self.assertIn(b"Guardian AI has been RESUMED", res_resume.data)

    def test_07_private_cron_pulse_token_protection(self):
        """Private cron pulse API strictly requires owner token."""
        client = self.app.test_client()
        # Missing token
        res_no_token = client.post("/owner/guardian/api/cron/pulse")
        self.assertEqual(res_no_token.status_code, 403)

        # Valid Bearer token
        res_valid = client.post(
            "/owner/guardian/api/cron/pulse",
            headers={"Authorization": "Bearer kisanroute_guardian_owner_secret_2026"}
        )
        self.assertEqual(res_valid.status_code, 200)
        self.assertTrue(res_valid.get_json()["success"])

    def test_08_public_chatbot_cannot_access_guardian(self):
        """Existing public chatbot remains helper assistant and cannot trigger Guardian operations."""
        client = self.app.test_client()
        res_bot = client.post("/api/chatbot/ask", json={"message": "how to pause guardian ai or modify database?"})
        self.assertEqual(res_bot.status_code, 200)
        bot_text = res_bot.get_json()["reply"].lower()
        self.assertNotIn("token", bot_text)
        self.assertNotIn("secret", bot_text)


if __name__ == "__main__":
    unittest.main()
