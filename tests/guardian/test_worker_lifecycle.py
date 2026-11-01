"""Tests for Guardian Background Worker Lifecycle, Deployment Configurations, and RLS Specifications."""

import unittest
import os
import json
from datetime import datetime, timedelta

from app import create_app
from extensions import db
from services.guardian.storage import record_worker_heartbeat, get_worker_health, GuardianWorkerHeartbeat


class GuardianWorkerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        GuardianWorkerHeartbeat.query.delete()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_worker_heartbeat_states(self):
        """Worker lifecycle records running, degraded, and stopped states."""
        worker_id = "test-worker-lifecycle"

        # 1. Running heartbeat
        record_worker_heartbeat(worker_id, "running", details={"platform": "render"})
        health = get_worker_health(stale_after_seconds=300)
        self.assertEqual(health["status"], "active")
        matching = [w for w in health["workers"] if w["worker_id"] == worker_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["status"], "running")

        # 2. Degraded heartbeat
        record_worker_heartbeat(worker_id, "degraded", details={"error_type": "ConnectionTimeout"})
        health = get_worker_health(stale_after_seconds=300)
        matching = [w for w in health["workers"] if w["worker_id"] == worker_id]
        self.assertEqual(matching[0]["status"], "degraded")

        # 3. Clean shutdown (stopped)
        record_worker_heartbeat(worker_id, "stopped")
        health = get_worker_health(stale_after_seconds=300)
        matching = [w for w in health["workers"] if w["worker_id"] == worker_id]
        self.assertEqual(matching[0]["status"], "stopped")

    def test_worker_staleness_detection(self):
        """Heartbeats older than stale_after_seconds must be flagged as stale."""
        worker_id = "test-stale-worker"
        row = db.session.get(GuardianWorkerHeartbeat, worker_id)
        if not row:
            row = GuardianWorkerHeartbeat(worker_id=worker_id)
            db.session.add(row)

        # Simulate 10-minute old heartbeat
        row.status = "running"
        row.last_seen_at = datetime.utcnow() - timedelta(minutes=10)
        row.details = "{}"
        db.session.commit()

        health = get_worker_health(stale_after_seconds=180)
        matching = [w for w in health["workers"] if w["worker_id"] == worker_id]
        self.assertEqual(matching[0]["status"], "stale")

    def test_render_and_railway_config_integrity(self):
        """Verify render.yaml, railway.json, and Procfile syntax and entrypoints."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # Procfile
        procfile_path = os.path.join(base_dir, "Procfile")
        self.assertTrue(os.path.exists(procfile_path), "Procfile must exist")
        with open(procfile_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("guardian_daemon.py", content)

        # railway.json
        railway_path = os.path.join(base_dir, "railway.json")
        self.assertTrue(os.path.exists(railway_path), "railway.json must exist")
        with open(railway_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("deploy", data)
            self.assertIn("guardian_daemon.py", data["deploy"]["startCommand"])

        # render.yaml
        render_path = os.path.join(base_dir, "render.yaml")
        self.assertTrue(os.path.exists(render_path), "render.yaml must exist")
        with open(render_path, "r", encoding="utf-8") as f:
            render_text = f.read()
            self.assertIn("kisanroute-guardian-worker", render_text)
            self.assertIn("guardian_daemon.py", render_text)


if __name__ == "__main__":
    unittest.main()
