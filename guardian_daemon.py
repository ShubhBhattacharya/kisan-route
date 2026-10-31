#!/usr/bin/env python3
"""KisanRoute Guardian AI - Persistent Background Worker Daemon.

Runs independent of web browsers or active user sessions.
Executes scheduled monitoring passes, synthetic workflow probes, auto-remediations,
and health checks across configured intervals.
"""

import os
import sys
import time
import signal
import argparse

# Ensure project root is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from services.guardian import guardian_service, get_state
from services.guardian.storage import append_log

RUNNING = True


def signal_handler(sig, frame):
    global RUNNING
    print("\n[Guardian Daemon] Graceful shutdown signal received. Stopping worker...")
    RUNNING = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_daemon(interval_seconds: int = 120, once: bool = False):
    """Start the persistent continuous reliability loop."""
    print("=" * 70)
    print("  [KISANROUTE GUARDIAN AI] PERSISTENT BACKGROUND SENTINEL")
    print(f"  Mode: {'Single-Pass Verification' if once else 'Continuous Autonomous Daemon'}")
    print(f"  Execution Interval: {interval_seconds} seconds")
    print("  Zero Browser Dependency | Multi-Model Intelligence | 3-Tier Safety")
    print("=" * 70)

    append_log(
        "DAEMON_STARTUP",
        f"Guardian AI standalone daemon process initialized (PID {os.getpid()}). Interval: {interval_seconds}s.",
        level="INFO"
    )

    iteration = 0
    while RUNNING:
        iteration += 1
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{current_time}] Starting Guardian Autonomous Cycle #{iteration}...")

        try:
            result = guardian_service.run_cycle(trigger_source=f"daemon_worker_iter_{iteration}")
            status = result.get("overall_health", "unknown")
            duration = result.get("duration_sec", 0)
            fixes = len(result.get("remediations", []))
            print(f"  -> Result: {status.upper()} in {duration}s | Fixes Evaluated: {fixes}")

            state = get_state()
            print(f"  -> Sentinel State: {state.get('status')} | Active Alerts: {state.get('active_alerts_count')}")

        except Exception as e:
            print(f"  [ERROR] Unhandled exception in Guardian cycle: {e}")
            append_log("DAEMON_CYCLE_ERROR", f"Daemon iteration {iteration} error: {e}", level="CRITICAL")

        if once:
            break

        print(f"Sleeping for {interval_seconds} seconds until next scheduled cycle...")
        for _ in range(interval_seconds):
            if not RUNNING:
                break
            time.sleep(1)

    print("[Guardian Daemon] Sentinel stopped cleanly.")
    append_log("DAEMON_STOPPED", "Guardian AI daemon process terminated gracefully.", level="INFO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KisanRoute Guardian AI Background Sentinel")
    parser.add_argument("--interval", type=int, default=120, help="Interval in seconds between inspection cycles (default: 120)")
    parser.add_argument("--once", action="store_true", help="Run a single audit cycle and exit")
    args = parser.parse_args()

    run_daemon(interval_seconds=args.interval, once=args.once)
