#!/usr/bin/env python3
"""Persistent Guardian worker. Run as a dedicated background process."""
import argparse
import os
import signal
import socket
import time
from datetime import datetime

from app import app
from extensions import db
from services.guardian import guardian_service
from services.guardian.storage import append_log, record_worker_heartbeat

RUNNING = True


def signal_handler(sig, frame):
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def validate_database_uri(uri: str | None) -> str:
    """Validate that the worker is configured with a persistent PostgreSQL URI.

    Fails fast if missing, empty, or configured for SQLite.
    Accepts postgresql:// and postgres://.
    """
    if not uri or not str(uri).strip():
        raise RuntimeError(
            "Persistent PostgreSQL DATABASE_URL is mandatory for the Guardian worker; no database URL configured."
        )
    normalized = str(uri).strip().lower()
    if normalized.startswith("sqlite:") or ":memory:" in normalized:
        raise RuntimeError(
            "Persistent PostgreSQL DATABASE_URL is mandatory for the Guardian worker; SQLite is strictly prohibited."
        )
    if not (normalized.startswith("postgresql://") or normalized.startswith("postgres://")):
        scheme = uri.split("://")[0] if "://" in uri else "unknown"
        raise RuntimeError(
            f"Invalid database scheme for Guardian worker: expected postgresql://, got '{scheme}'."
        )
    return uri


def run_daemon(interval_seconds=120, once=False):
    if interval_seconds < 30:
        raise ValueError("Worker interval must be at least 30 seconds.")

    with app.app_context():
        # Enforce PostgreSQL configuration for the persistent worker process
        env_db = (
            os.environ.get("DATABASE_URL")
            or os.environ.get("SUPABASE_DB_URL")
            or os.environ.get("KISAN_ROUTE_DATABASE_URL")
        )
        db_uri = env_db or app.config.get("SQLALCHEMY_DATABASE_URI")
        if not env_db and (not db_uri or str(db_uri).startswith("sqlite:")):
            raise RuntimeError(
                "Persistent PostgreSQL DATABASE_URL is mandatory for the Guardian worker; missing DATABASE_URL environment variable."
            )
        validate_database_uri(db_uri)

        worker_id = os.environ.get("GUARDIAN_WORKER_ID") or socket.gethostname()

        # Startup recording
        try:
            record_worker_heartbeat(worker_id, "running")
            append_log("DAEMON_STARTUP", f"Guardian worker {worker_id} started", level="INFO")
            print(f"[Guardian] worker {worker_id} started successfully.")
        except Exception as startup_exc:
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f"[Guardian] Worker startup failed to record in database: {startup_exc}")
            raise

        while RUNNING:
            cycle_at = None
            try:
                record_worker_heartbeat(worker_id, "running")
                result = guardian_service.run_cycle(trigger_source=f"worker:{worker_id}")
                cycle_at = datetime.utcnow()
                record_worker_heartbeat(
                    worker_id,
                    "running",
                    last_cycle_at=cycle_at,
                    details={"last_result": result.get("status", "unknown")},
                )
                print(f"[Guardian] cycle={result.get('status')} worker={worker_id}")
            except Exception as exc:
                # Roll back broken session immediately so aborted transactions don't poison subsequent queries
                try:
                    db.session.rollback()
                except Exception as rb_exc:
                    print(f"[Guardian] session rollback error: {rb_exc}")

                # Attempt to record degraded heartbeat and cycle error log
                try:
                    record_worker_heartbeat(
                        worker_id,
                        "degraded",
                        details={"error_type": type(exc).__name__, "error": str(exc)[:200]},
                    )
                    append_log(
                        "DAEMON_CYCLE_ERROR",
                        f"Guardian worker cycle failed: {type(exc).__name__}",
                        level="ERROR",
                    )
                except Exception as telemetry_exc:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    print(f"[Guardian] telemetry unavailable (database down): {type(telemetry_exc).__name__}")
                print(f"[Guardian] cycle failed: {type(exc).__name__}: {exc}")

            if once:
                break
            for _ in range(interval_seconds):
                if not RUNNING:
                    break
                time.sleep(1)

        # Graceful Shutdown
        try:
            db.session.rollback()
            record_worker_heartbeat(worker_id, "stopped", details={"reason": "clean_shutdown"})
            append_log("DAEMON_STOPPED", f"Guardian worker {worker_id} stopped", level="INFO")
            print(f"[Guardian] worker {worker_id} stopped cleanly.")
        except Exception as stop_exc:
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f"[Guardian] Warning: could not record stopped heartbeat on shutdown: {type(stop_exc).__name__}: {stop_exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=120)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    run_daemon(args.interval, args.once)
