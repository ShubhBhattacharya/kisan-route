#!/usr/bin/env python3
"""Persistent Guardian worker. Run as a dedicated background process."""
import argparse
import os
import signal
import socket
import time
from datetime import datetime

from app import create_app
from services.guardian import guardian_service
from services.guardian.storage import append_log, record_worker_heartbeat

RUNNING = True


def signal_handler(sig, frame):
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_daemon(interval_seconds=120, once=False):
    if interval_seconds < 30:
        raise ValueError("Worker interval must be at least 30 seconds.")
    app = create_app()
    worker_id = os.environ.get("GUARDIAN_WORKER_ID") or socket.gethostname()
    with app.app_context():
        append_log("DAEMON_STARTUP", f"Guardian worker {worker_id} started", level="INFO")
        while RUNNING:
            cycle_at = None
            try:
                record_worker_heartbeat(worker_id, "running")
                result = guardian_service.run_cycle(trigger_source=f"worker:{worker_id}")
                cycle_at = datetime.utcnow()
                record_worker_heartbeat(worker_id, "running", last_cycle_at=cycle_at,
                                         details={"last_result": result.get("status", "unknown")})
                print(f"[Guardian] cycle={result.get('status')} worker={worker_id}")
            except Exception as exc:
                record_worker_heartbeat(worker_id, "degraded",
                                         details={"error_type": type(exc).__name__})
                append_log("DAEMON_CYCLE_ERROR", f"Guardian worker cycle failed: {type(exc).__name__}",
                           level="ERROR")
                print(f"[Guardian] cycle failed: {type(exc).__name__}")
            if once:
                break
            for _ in range(interval_seconds):
                if not RUNNING:
                    break
                time.sleep(1)
        record_worker_heartbeat(worker_id, "stopped")
        append_log("DAEMON_STOPPED", f"Guardian worker {worker_id} stopped", level="INFO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=120)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    run_daemon(args.interval, args.once)
