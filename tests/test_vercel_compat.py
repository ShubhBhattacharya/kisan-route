"""
Regression tests for Vercel Python runtime compatibility and production startup safety.

Vercel requires the module-level 'app', 'application', or 'handler' symbol in app.py
to be a valid WSGI callable at import time. These tests ensure:

  1. app, application, and handler symbols exist and are callable in normal,
     worker, and Vercel environments.
  2. The _LazyApp wrapper delegates attribute access to the real Flask app.
  3. Production startup safety: create_app() never executes uncontrolled
     db.create_all() or database queries at startup in production/Vercel/worker modes.
  4. Configuration guard:
     - Missing SECRET_KEY on Vercel raises RuntimeError on request.
     - SQLite on Vercel raises RuntimeError on request.
     - Failed validation leaves _vercel_config_checked as False so subsequent
       requests cannot bypass validation.
     - Valid production config passes and marks _vercel_config_checked as True.
"""

import importlib
import os
import sys
import unittest
from unittest.mock import patch


class TestVercelEntrypoint(unittest.TestCase):
    """app.py must expose valid WSGI callables as module-level 'app', 'application', and 'handler'."""

    def _reload_app_module(self, env_overrides=None):
        """
        Reload app.py with custom environment variables set.
        Cleans up the cached module after each sub-test to avoid state leakage.
        """
        env_backup = os.environ.copy()
        try:
            # Baseline test environment
            os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
            os.environ.pop("KISAN_ROUTE_SECRET_KEY", None)
            os.environ.pop("SECRET_KEY", None)
            os.environ.pop("KISAN_WORKER_MODE", None)
            os.environ.pop("VERCEL", None)

            if env_overrides:
                for k, v in env_overrides.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

            sys.modules.pop("app", None)
            app_module = importlib.import_module("app")
            return app_module
        finally:
            os.environ.clear()
            os.environ.update(env_backup)
            sys.modules.pop("app", None)

    def test_app_is_not_none_in_normal_mode(self):
        """app.app must be a non-None WSGI callable in normal (non-worker) mode."""
        mod = self._reload_app_module()
        self.assertIsNotNone(mod.app, "app.app must not be None at import time")
        self.assertTrue(callable(mod.app), "app.app must be callable")

    def test_application_and_handler_aliases_exist(self):
        """application and handler must alias app for standard WSGI/Vercel discovery."""
        mod = self._reload_app_module()
        self.assertIs(mod.application, mod.app, "application must alias app")
        self.assertIs(mod.handler, mod.app, "handler must alias app")

    def test_app_in_worker_mode(self):
        """app.app must be a valid WSGI placeholder in KISAN_WORKER_MODE=1."""
        mod = self._reload_app_module({"KISAN_WORKER_MODE": "1"})
        self.assertIsNotNone(mod.app)
        self.assertTrue(callable(mod.app))
        self.assertIs(mod.application, mod.app)
        self.assertIs(mod.handler, mod.app)

    def test_app_in_vercel_mode(self):
        """app.app must be a valid _LazyApp in VERCEL=1 mode."""
        mod = self._reload_app_module({"VERCEL": "1"})
        self.assertIsNotNone(mod.app)
        self.assertTrue(callable(mod.app))
        self.assertIsInstance(mod.app, mod._LazyApp)
        self.assertIs(mod.application, mod.app)
        self.assertIs(mod.handler, mod.app)

    def test_lazy_app_delegates_attributes(self):
        """_LazyApp must delegate unknown attribute access to the real Flask app."""
        mod = self._reload_app_module({"KISAN_WORKER_MODE": "1"})
        lazy = mod.app
        self.assertIsNotNone(lazy.config)


class TestProductionStartupSafety(unittest.TestCase):
    """Production startup must never perform uncontrolled db.create_all()."""

    def setUp(self):
        self.env_backup = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env_backup)
        sys.modules.pop("app", None)

    def test_create_all_not_called_in_vercel_mode(self):
        """In VERCEL mode, create_app() must NOT call db.create_all()."""
        os.environ["VERCEL"] = "1"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@ep-staging.ap-south-1.aws.neon.tech/kisanroute"
        os.environ["SECRET_KEY"] = "test-secret-key-for-unit-test"

        with patch("extensions.db.create_all") as mock_create_all:
            from app import create_app
            app = create_app()
            mock_create_all.assert_not_called()

    def test_create_all_not_called_in_worker_mode(self):
        """In worker mode, create_app() must NOT call db.create_all()."""
        os.environ["KISAN_WORKER_MODE"] = "1"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@ep-staging.ap-south-1.aws.neon.tech/kisanroute"

        with patch("extensions.db.create_all") as mock_create_all:
            from app import create_app
            app = create_app(config_override={"SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@ep-staging.ap-south-1.aws.neon.tech/kisanroute"})
            mock_create_all.assert_not_called()

    def test_create_all_not_called_for_postgresql_database(self):
        """When connected to PostgreSQL, create_app() must NOT call db.create_all()."""
        with patch("extensions.db.create_all") as mock_create_all:
            from app import create_app
            app = create_app(config_override={"SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@ep-staging.ap-south-1.aws.neon.tech/kisanroute"})
            mock_create_all.assert_not_called()


class TestConfigurationGuard(unittest.TestCase):
    """Test Vercel production configuration guard and regression handling."""

    def setUp(self):
        self.env_backup = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env_backup)
        sys.modules.pop("app", None)

    def test_guard_fails_when_secret_key_missing_on_vercel(self):
        """Request fails with RuntimeError when SECRET_KEY is missing on Vercel."""
        os.environ["VERCEL"] = "1"
        os.environ.pop("SECRET_KEY", None)
        os.environ.pop("KISAN_ROUTE_SECRET_KEY", None)

        from app import create_app
        app = create_app(config_override={
            "SECRET_KEY": "",
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
        })

        # Verification flag starts False
        self.assertFalse(app._vercel_config_checked[0])

        client = app.test_client()
        with self.assertRaises(RuntimeError) as ctx:
            client.get("/")
        self.assertIn("SECRET_KEY must be configured", str(ctx.exception))

        # Failed validation must NOT set checked flag to True
        self.assertFalse(
            app._vercel_config_checked[0],
            "Failed validation must leave _vercel_config_checked as False"
        )

        # Subsequent request must also fail (not bypass)
        with self.assertRaises(RuntimeError) as ctx2:
            client.get("/")
        self.assertIn("SECRET_KEY must be configured", str(ctx2.exception))
        self.assertFalse(app._vercel_config_checked[0])

    def test_guard_rejects_sqlite_in_production(self):
        """Request fails with RuntimeError when SQLite is configured on Vercel."""
        os.environ["VERCEL"] = "1"

        from app import create_app
        app = create_app(config_override={
            "SECRET_KEY": "a-valid-production-secret-key-32chars",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///local.db",
            "TESTING": True
        })

        client = app.test_client()
        with self.assertRaises(RuntimeError) as ctx:
            client.get("/")
        self.assertIn("SQLite is strictly prohibited", str(ctx.exception))
        self.assertFalse(app._vercel_config_checked[0])

        # Subsequent request must also fail
        with self.assertRaises(RuntimeError) as ctx2:
            client.get("/")
        self.assertIn("SQLite is strictly prohibited", str(ctx2.exception))
        self.assertFalse(app._vercel_config_checked[0])

    def test_guard_rejects_non_postgresql_scheme(self):
        """Request fails with RuntimeError when database scheme is not postgresql."""
        os.environ["VERCEL"] = "1"

        from app import create_app
        app = create_app(config_override={
            "SECRET_KEY": "a-valid-production-secret-key-32chars",
            "SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@ep-staging.ap-south-1.aws.neon.tech/kisanroute",
            "TESTING": True
        })
        os.environ["DATABASE_URL"] = "http://invalid-database-host"

        client = app.test_client()
        with self.assertRaises(RuntimeError) as ctx:
            client.get("/")
        self.assertIn("expected postgresql:// URI", str(ctx.exception))
        self.assertFalse(app._vercel_config_checked[0])

    def test_guard_succeeds_with_valid_postgresql_config(self):
        """With valid PostgreSQL and SECRET_KEY, request passes and sets checked flag to True."""
        os.environ["VERCEL"] = "1"

        from app import create_app
        app = create_app(config_override={
            "SECRET_KEY": "a-valid-production-secret-key-32chars",
            "SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@ep-staging.ap-south-1.aws.neon.tech/kisanroute",
            "TESTING": True
        })

        self.assertFalse(app._vercel_config_checked[0])

        client = app.test_client()
        response = client.get("/manifest.json")
        self.assertIn(response.status_code, (200, 404))

        # Flag must now be marked True
        self.assertTrue(
            app._vercel_config_checked[0],
            "Successful validation must mark _vercel_config_checked as True"
        )

        # Subsequent request should reuse checked state (fast path)
        response2 = client.get("/manifest.json")
        self.assertIn(response2.status_code, (200, 404))
        self.assertTrue(app._vercel_config_checked[0])


if __name__ == "__main__":
    unittest.main()
