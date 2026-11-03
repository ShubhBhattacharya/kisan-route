"""Tests for Guardian Background Worker Lifecycle, Deployment Configurations, and RLS Specifications."""

import unittest
import os
import sys
import json
import signal
import subprocess
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Force in-memory database before any test app imports
os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

from app import create_app
from extensions import db
from services.guardian.storage import record_worker_heartbeat, get_worker_health, GuardianWorkerHeartbeat
from guardian_daemon import validate_database_uri, signal_handler, run_daemon, get_worker_database_uri
import guardian_daemon


class GuardianWorkerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
        cls.app = create_app(config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
        })
        with cls.app.app_context():
            db.create_all()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        GuardianWorkerHeartbeat.query.delete()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    # --- Heartbeat & Staleness ---

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

        row.status = "running"
        row.last_seen_at = datetime.utcnow() - timedelta(minutes=10)
        row.details = "{}"
        db.session.commit()

        health = get_worker_health(stale_after_seconds=180)
        matching = [w for w in health["workers"] if w["worker_id"] == worker_id]
        self.assertEqual(matching[0]["status"], "stale")

    # --- Database URI Validation & SQLite Rejection ---

    def test_validate_database_uri_rejects_missing(self):
        """Worker must fail fast if database URI is missing or empty."""
        with self.assertRaises(RuntimeError) as cm:
            validate_database_uri(None)
        self.assertIn("mandatory", str(cm.exception))

        with self.assertRaises(RuntimeError) as cm:
            validate_database_uri("   ")
        self.assertIn("mandatory", str(cm.exception))

    def test_validate_database_uri_rejects_sqlite(self):
        """Worker must fail fast and reject SQLite configurations."""
        with self.assertRaises(RuntimeError) as cm:
            validate_database_uri("sqlite:///kisanroute.db")
        self.assertIn("SQLite is strictly prohibited", str(cm.exception))

        with self.assertRaises(RuntimeError) as cm:
            validate_database_uri("sqlite:///:memory:")
        self.assertIn("SQLite is strictly prohibited", str(cm.exception))

    def test_validate_database_uri_rejects_non_postgres(self):
        """Worker must reject non-PostgreSQL database schemes."""
        with self.assertRaises(RuntimeError) as cm:
            validate_database_uri("mysql://user:pass@localhost/db")
        self.assertIn("expected postgresql://", str(cm.exception))

    def test_validate_database_uri_accepts_postgres(self):
        """Worker accepts postgresql:// and postgres:// connection strings."""
        pg_uri = "postgresql://user:pass@ep-cool-host.ap-south-1.aws.neon.tech/kisanroute?sslmode=require"
        self.assertEqual(validate_database_uri(pg_uri), pg_uri)

        legacy_uri = "postgres://user:pass@db.supabase.co:6543/postgres"
        self.assertEqual(validate_database_uri(legacy_uri), legacy_uri)

    # --- Initialization Order: Validation BEFORE Flask or DB Creation ---

    def test_worker_fails_before_app_creation_on_missing_db(self):
        """Worker fails fast on missing DB without initializing Flask app or creating tables."""
        env_clean = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "SUPABASE_DB_URL", "KISAN_ROUTE_DATABASE_URL")}
        with patch.dict(os.environ, env_clean, clear=True):
            with patch("guardian_daemon.init_worker_app") as mock_init:
                with self.assertRaises(RuntimeError) as cm:
                    run_daemon(once=True)
                self.assertIn("mandatory", str(cm.exception))
                mock_init.assert_not_called()

    def test_worker_fails_before_app_creation_on_sqlite(self):
        """Worker fails fast on SQLite without initializing Flask app or creating tables."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///kisanroute.db"}):
            with patch("guardian_daemon.init_worker_app") as mock_init:
                with self.assertRaises(RuntimeError) as cm:
                    run_daemon(once=True)
                self.assertIn("SQLite is strictly prohibited", str(cm.exception))
                mock_init.assert_not_called()

    # --- Worker Startup Failure Handling ---

    def test_worker_startup_failure_rolls_back_and_fails_fast(self):
        """Worker startup rolls back database session and raises if initial heartbeat fails."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock:mock@localhost:5432/mock"}):
            with patch("guardian_daemon.validate_database_uri", return_value="postgresql://mock:mock@localhost:5432/mock"):
                with patch("guardian_daemon.init_worker_app", return_value=self.app):
                    with patch("services.guardian.storage.record_worker_heartbeat", side_effect=Exception("DB connection refused")):
                        with patch.object(db.session, "rollback") as mock_rollback:
                            with self.assertRaises(Exception) as cm:
                                run_daemon(once=True, app=self.app)
                            self.assertIn("DB connection refused", str(cm.exception))
                            mock_rollback.assert_called()

    # --- Worker Cycle Error & Session Recovery ---

    def test_worker_cycle_error_db_recovery(self):
        """Worker rolls back session on cycle error and records degraded state."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock:mock@localhost:5432/mock"}):
            with patch("guardian_daemon.validate_database_uri", return_value="postgresql://mock:mock@localhost:5432/mock"):
                with patch("services.guardian.guardian_service.run_cycle", side_effect=RuntimeError("Synthetic check timeout")):
                    with patch.object(db.session, "rollback") as mock_rollback:
                        with patch("services.guardian.storage.record_worker_heartbeat") as mock_heartbeat:
                            with patch("services.guardian.storage.append_log"):
                                run_daemon(once=True, app=self.app)
                                mock_rollback.assert_called()
                                degraded_calls = [
                                    call for call in mock_heartbeat.call_args_list
                                    if len(call.args) > 1 and call.args[1] == "degraded"
                                ]
                                self.assertTrue(len(degraded_calls) >= 1)

    # --- Worker Lifecycle Reentrancy & Signal Handling ---

    def test_worker_repeated_invocations_in_same_process(self):
        """Worker resets RUNNING flag and runs successfully across repeated invocations in the same process."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock:mock@localhost:5432/mock"}):
            with patch("guardian_daemon.validate_database_uri", return_value="postgresql://mock:mock@localhost:5432/mock"):
                with patch("services.guardian.guardian_service.run_cycle", return_value={"status": "healthy"}):
                    # Run 1
                    run_daemon(once=True, app=self.app)
                    self.assertTrue(guardian_daemon.RUNNING)

                    # Run 2 in same process
                    run_daemon(once=True, app=self.app)
                    self.assertTrue(guardian_daemon.RUNNING)

    def test_worker_sigterm_shutdown_and_subsequent_restart(self):
        """Worker catches SIGTERM, shuts down cleanly, and restarts properly on subsequent invocation."""
        guardian_daemon.RUNNING = True
        signal_handler(signal.SIGTERM, None)
        self.assertFalse(guardian_daemon.RUNNING)

        # Subsequent call must reset RUNNING to True and complete
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock:mock@localhost:5432/mock"}):
            with patch("guardian_daemon.validate_database_uri", return_value="postgresql://mock:mock@localhost:5432/mock"):
                with patch("services.guardian.guardian_service.run_cycle", return_value={"status": "healthy"}):
                    run_daemon(once=True, app=self.app)
                    self.assertTrue(guardian_daemon.RUNNING)

    def test_worker_shutdown_db_error_does_not_crash(self):
        """Worker catches database failure during shutdown and exits cleanly with rollback."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock:mock@localhost:5432/mock"}):
            with patch("guardian_daemon.validate_database_uri", return_value="postgresql://mock:mock@localhost:5432/mock"):
                with patch("services.guardian.storage.append_log"):
                    mock_hb = MagicMock(side_effect=[None, RuntimeError("DB gone during shutdown")])
                    with patch("services.guardian.storage.record_worker_heartbeat", mock_hb):
                        with patch.object(db.session, "rollback") as mock_rollback:
                            try:
                                run_daemon(once=True, app=self.app)
                            except Exception as e:
                                self.fail(f"run_daemon raised unhandled exception during shutdown DB error: {e}")
                            mock_rollback.assert_called()

    # --- Process-Level Subprocess Tests ---

    def test_process_level_worker_rejection_without_touching_db(self):
        """Process-level test: executing guardian_daemon.py with missing DATABASE_URL fails fast with code 1."""
        env = os.environ.copy()
        env.pop("DATABASE_URL", None)
        env.pop("SUPABASE_DB_URL", None)
        env.pop("KISAN_ROUTE_DATABASE_URL", None)

        proc = subprocess.run(
            [sys.executable, "guardian_daemon.py", "--once"],
            capture_output=True,
            text=True,
            env=env,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Persistent PostgreSQL DATABASE_URL is mandatory", proc.stderr)

    # --- Deployment Configuration & Security Integrity ---

    def test_render_and_railway_config_integrity(self):
        """Verify render.yaml, railway.json, and Procfile syntax, region, and security."""
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
            self.assertIn("region: singapore", render_text)
            self.assertNotIn("OWNER_PIN", render_text)
            self.assertNotIn("OWNER_TOKEN", render_text)

    def test_python_version_file_pinned(self):
        """Verify .python-version exists and explicitly pins Vercel-compatible Python 3.12."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        version_file = os.path.join(base_dir, ".python-version")
        self.assertTrue(os.path.exists(version_file), ".python-version must exist")
        with open(version_file, "r", encoding="utf-8") as f:
            version = f.read().strip()
        self.assertEqual(version, "3.12", f"Expected Vercel-compatible '3.12', got: '{version}'")

    def test_proposed_rls_migration_covers_all_six_guardian_tables(self):
        """Verify proposed RLS specification exists and protects all six Guardian tables."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        rls_file = os.path.join(base_dir, "migrations", "sql", "002_propose_guardian_rls_design.sql")
        self.assertTrue(os.path.exists(rls_file), "002_propose_guardian_rls_design.sql must exist")

        with open(rls_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Must explicitly warn that it is a specification / proposal only
        self.assertIn("STATUS: PROPOSED", sql_content)
        self.assertIn("DO NOT APPLY DIRECTLY", sql_content)

        guardian_tables = [
            "guardian_state",
            "guardian_logs",
            "guardian_issues",
            "guardian_patches",
            "guardian_worker_heartbeats",
            "guardian_import_ledger",
        ]

        for table in guardian_tables:
            # 1. RLS must be enabled
            enable_stmt = f"ALTER TABLE IF EXISTS {table} ENABLE ROW LEVEL SECURITY;"
            self.assertIn(enable_stmt, sql_content, f"Missing ENABLE ROW LEVEL SECURITY for {table}")

            # 2. Privileges must be revoked from anon and authenticated
            revoke_stmt = f"REVOKE ALL ON TABLE {table} FROM anon, authenticated;"
            self.assertIn(revoke_stmt, sql_content, f"Missing REVOKE ALL for {table}")

            # 3. service_role policy must be defined
            policy_stmt = f"{table}_service_role_policy"
            self.assertIn(policy_stmt, sql_content, f"Missing service_role policy for {table}")


if __name__ == "__main__":
    unittest.main()
