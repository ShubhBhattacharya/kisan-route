"""
Regression tests for Vercel Python runtime compatibility.

Vercel requires the module-level 'app' symbol in app.py to be a valid WSGI
callable at import time.  These tests ensure:

  1. app.app is never None regardless of KISAN_WORKER_MODE.
  2. app.app is always callable (satisfies WSGI contract).
  3. The _LazyApp wrapper delegates attribute access to the real Flask app.
  4. Guardian worker mode does not break the module-level symbol.
"""

import importlib
import os
import sys
import unittest


class TestVercelEntrypoint(unittest.TestCase):
    """app.py must always expose a valid WSGI callable as its module-level 'app'."""

    def _reload_app_module(self, env_overrides=None):
        """
        Reload app.py with custom environment variables set.
        Cleans up the cached module after each sub-test to avoid state leakage.
        """
        env_backup = os.environ.copy()
        try:
            # Apply test environment
            os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
            os.environ.pop("KISAN_ROUTE_SECRET_KEY", None)
            os.environ.pop("SECRET_KEY", None)
            # Ensure we are NOT in worker mode unless the test requests it
            os.environ.pop("KISAN_WORKER_MODE", None)

            if env_overrides:
                for k, v in env_overrides.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

            # Remove cached module so re-import is fresh
            sys.modules.pop("app", None)
            app_module = importlib.import_module("app")
            return app_module
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(env_backup)
            sys.modules.pop("app", None)

    def test_app_is_not_none_in_normal_mode(self):
        """app.app must be a non-None WSGI callable in normal (non-worker) mode."""
        mod = self._reload_app_module()
        self.assertIsNotNone(mod.app, "app.app must not be None at import time")

    def test_app_is_callable_in_normal_mode(self):
        """app.app must be callable (WSGI contract) in normal mode."""
        mod = self._reload_app_module()
        self.assertTrue(callable(mod.app), "app.app must be a callable WSGI object")

    def test_app_is_not_none_in_worker_mode(self):
        """app.app must be a valid WSGI placeholder even in KISAN_WORKER_MODE=1."""
        mod = self._reload_app_module({"KISAN_WORKER_MODE": "1"})
        self.assertIsNotNone(
            mod.app,
            "app.app must not be None even in worker mode; Vercel entrypoint requires a callable.",
        )

    def test_app_is_callable_in_worker_mode(self):
        """app.app in worker mode (_LazyApp) must be callable."""
        mod = self._reload_app_module({"KISAN_WORKER_MODE": "1"})
        self.assertTrue(
            callable(mod.app),
            "app.app (_LazyApp wrapper) must be callable in worker mode.",
        )

    def test_lazy_app_class_exists(self):
        """_LazyApp must be defined in app.py."""
        mod = self._reload_app_module()
        self.assertTrue(
            hasattr(mod, "_LazyApp"),
            "_LazyApp wrapper class must be present in app.py",
        )

    def test_lazy_app_delegates_attributes(self):
        """_LazyApp must delegate unknown attribute access to the real Flask app."""
        mod = self._reload_app_module({"KISAN_WORKER_MODE": "1"})
        lazy = mod.app
        # Accessing .config should delegate to the real Flask app via __getattr__
        self.assertIsNotNone(
            lazy.config,
            "_LazyApp must delegate .config to the underlying Flask app",
        )


if __name__ == "__main__":
    unittest.main()
