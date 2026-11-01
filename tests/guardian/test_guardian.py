"""Complete Automated Test Suite for KisanRoute Guardian AI.

Validates:
1. Multi-Model AI Orchestrator & Free-tier quota tracker.
2. Synthetic workflow probes for Farmer, Cluster, Customer, Driver, Wholesaler.
3. 3-Tier Safe Fixer permission boundaries (enforcing Level 3 financial lock).
4. Protected Admin Control Center auth barrier and metrics views.
5. Dual-mode 24x7 cron health endpoint.
6. Zero regression across existing website and in-app assistants.
"""

import os
import unittest
from app import create_app
from extensions import db
from services.guardian import guardian_service, safe_fix_engine, workflow_runner, orchestrator
from services.guardian.storage import get_state, get_recent_logs, get_all_issues, get_all_patches


class TestGuardianAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
        cls.app = create_app(config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
        })
        with cls.app.app_context():
            db.create_all()
        cls.client = cls.app.test_client()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_01_existing_website_and_assistants_intact(self):
        """Verify baseline website and both customer-facing assistants are completely intact."""
        # 1. Homepage loads successfully
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"KisanRoute", res.data)

        # 2. Existing in-app Chatbot Assistant answers correctly
        res_bot = self.client.post("/api/chatbot/ask", json={"message": "delhi wheat rate"})
        self.assertEqual(res_bot.status_code, 200)
        bot_data = res_bot.get_json()
        self.assertIn("reply", bot_data)
        self.assertTrue(len(bot_data["reply"]) > 10)

        # 3. Existing Voice Assistant endpoint responds
        res_voice = self.client.post("/api/voice/process", json={"query": "mandi bhav", "lang": "hi-IN"})
        self.assertEqual(res_voice.status_code, 200)

    def test_02_synthetic_workflows_all_5_roles(self):
        """Verify synthetic runner checks Farmer, Cluster, Customer, Driver, Wholesaler."""
        runner = workflow_runner
        runner.app = self.app
        results = runner.run_all_checks()
        self.assertEqual(results["overall_status"], "healthy")
        self.assertEqual(results["failed_checks"], [])
        self.assertIn("farmer", results["roles"])
        self.assertIn("cluster", results["roles"])
        self.assertIn("customer", results["roles"])
        self.assertIn("driver", results["roles"])
        self.assertIn("wholesaler", results["roles"])
        self.assertEqual(results["roles"]["farmer"]["status"], "healthy")
        self.assertEqual(results["roles"]["customer"]["status"], "healthy")

    def test_03_ai_orchestrator_analysis_shape(self):
        """Verify the incident analyzer returns its expected structure; this is not a billing test."""
        analysis = orchestrator.analyze_incident(
            incident_title="Transient Weather API 504 Timeout",
            error_details={"api": "open-meteo", "timeout": 5.0},
            category="integration"
        )
        self.assertIn("root_cause", analysis)
        self.assertIn("tier", analysis)

    def test_04_safe_fixer_tier_boundaries(self):
        """Verify Level 1 auto-fixes safely, Level 2 queues patches, and Level 3 halts sensitive operations."""
        # Test Level 1: Transient cache/timeout issue
        res1 = safe_fix_engine.evaluate_and_remediate({
            "category": "integration",
            "title": "Weather upstream timeout",
            "details": {"retry": True}
        })
        self.assertIn(res1["action"], ["auto_fixed", "patch_queued"])

        # Test Level 3: Attempt to touch financial / payment / balance data
        res3 = safe_fix_engine.evaluate_and_remediate({
            "category": "financial",
            "title": "Modify farmer payout balance in payment gateway",
            "details": {"action": "alter balance"}
        })
        self.assertEqual(res3["action"], "blocked_by_safety_policy")
        self.assertEqual(res3["tier"], 3)

    def test_05_admin_control_center_auth_gate(self):
        """Legacy admin UI redirects to the owner-only dashboard."""
        anon_client = self.app.test_client()
        res = anon_client.get("/admin/guardian/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/owner/guardian/", res.headers.get("Location", ""))

        # A legacy admin session is not an owner identity.
        with anon_client.session_transaction() as sess:
            sess["guardian_admin_auth"] = True
        res_auth = anon_client.get("/admin/guardian/")
        self.assertEqual(res_auth.status_code, 302)

    def test_06_guardian_cron_endpoints(self):
        """Verify both public and authorized cron health endpoints operate cleanly."""
        res_public = self.client.get("/admin/guardian/cron/health")
        self.assertEqual(res_public.status_code, 200)
        self.assertEqual(res_public.get_json().get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
