import unittest
from datetime import datetime, timedelta

from flask import Flask
from extensions import db
from services.guardian.storage import (
    get_state, update_state, append_log, get_recent_logs,
    record_issue, get_all_issues, resolve_issue,
    queue_patch, get_all_patches, update_patch_status,
    record_worker_heartbeat, get_worker_health,
)


class GuardianSQLStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask("guardian-storage-tests")
        cls.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(cls.app)
        with cls.app.app_context():
            db.create_all()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        # Isolate each test while retaining the shared in-memory schema.
        for model in reversed(list(db.metadata.sorted_tables)):
            db.session.execute(model.delete())
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_state_defaults_and_updates_persist(self):
        self.assertEqual(get_state()["status"], "not_configured")
        state = update_state({"execution_count": 3})
        self.assertEqual(state["execution_count"], 3)
        self.assertEqual(get_state()["execution_count"], 3)

    def test_logs_issues_and_resolution_persist(self):
        append_log("TEST", "storage test")
        self.assertEqual(get_recent_logs(1)[0]["event_type"], "TEST")
        record_issue("issue-1", "Test issue", "test", "low", {"safe": True})
        self.assertIn("issue-1", get_all_issues())
        resolve_issue("issue-1", "verified")
        self.assertEqual(get_all_issues()["issue-1"]["status"], "resolved")

    def test_patch_review_state_persists(self):
        queue_patch("patch-1", "issue-1", "Test patch", "diff", ["a.py"])
        update_patch_status("patch-1", "approved", "owner reviewed")
        self.assertEqual(get_all_patches()["patch-1"]["status"], "approved")

    def test_worker_heartbeat_and_staleness(self):
        record_worker_heartbeat("worker-test", "running", datetime.utcnow())
        self.assertEqual(get_worker_health()["status"], "active")
        row = db.session.get(__import__(
            "services.guardian.storage", fromlist=["GuardianWorkerHeartbeat"]
        ).GuardianWorkerHeartbeat, "worker-test")
        row.last_seen_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.commit()
        self.assertEqual(get_worker_health(stale_after_seconds=300)["workers"][0]["status"], "stale")


if __name__ == "__main__":
    unittest.main()
