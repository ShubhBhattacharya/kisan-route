"""KisanRoute Guardian AI - Main Service Orchestrator.

Combines the Sentinel, Workflow Runner, AI Orchestrator, and Safe Fixer into
a unified background supervisor callable via CLI, standalone daemon, or serverless cron.
"""

import time
from datetime import datetime
from services.guardian.storage import (
    get_state, update_state, append_log, get_recent_logs,
    get_all_issues, get_all_patches, update_patch_status
)
from services.guardian.workflow_runner import workflow_runner
from services.guardian.ai_orchestrator import orchestrator
from services.guardian.safe_fixer import safe_fix_engine


class GuardianAI:
    def __init__(self):
        pass

    def run_cycle(self, trigger_source: str = "manual"):
        """Execute one complete monitoring and self-healing inspection cycle."""
        state = get_state()
        if state.get("status") == "paused":
            append_log("GUARDIAN_CYCLE_SKIPPED", "Guardian AI cycle skipped because state is PAUSED.", level="INFO")
            return {"status": "paused", "message": "Guardian AI is currently paused by admin."}

        start_time = time.time()
        append_log("GUARDIAN_CYCLE_START", f"Guardian AI inspection cycle started (Trigger: {trigger_source}).", level="INFO")

        # 1. Run full synthetic workflow suite
        workflow_results = workflow_runner.run_all_checks()

        # 2. Process any degraded checks through the Safe Fix Engine
        fixes_applied = []
        if workflow_results.get("failed_checks"):
            for check in workflow_results["failed_checks"]:
                incident = {
                    "category": "workflow",
                    "title": f"Degraded component detected: {check}",
                    "details": {"trigger": trigger_source, "results": workflow_results}
                }
                fix_res = safe_fix_engine.evaluate_and_remediate(incident)
                fixes_applied.append(fix_res)

        duration = round(time.time() - start_time, 2)
        exec_count = state.get("execution_count", 0) + 1

        all_issues = get_all_issues()
        unresolved_count = sum(1 for i in all_issues.values() if i.get("status") in ["detected", "analyzing", "patch_pending"])
        all_patches = get_all_patches()
        pending_patches_count = sum(1 for p in all_patches.values() if p.get("status") == "pending_review")

        # 3. Update persistent state
        update_state({
            "last_execution": datetime.utcnow().isoformat(),
            "last_health_status": workflow_results.get("overall_status", "healthy"),
            "execution_count": exec_count,
            "active_alerts_count": unresolved_count,
            "pending_patches_count": pending_patches_count,
        })

        append_log(
            "GUARDIAN_CYCLE_COMPLETE",
            f"Cycle finished in {duration}s. Status: {workflow_results.get('overall_status')}. Fixes evaluated: {len(fixes_applied)}.",
            level="INFO",
            details={"duration_sec": duration, "fixes": len(fixes_applied)}
        )

        return {
            "status": "success",
            "duration_sec": duration,
            "overall_health": workflow_results.get("overall_status"),
            "workflow_results": workflow_results,
            "remediations": fixes_applied,
            "timestamp": datetime.utcnow().isoformat()
        }

    def pause(self):
        update_state({"status": "paused"})
        append_log("GUARDIAN_STATE_CHANGE", "Guardian AI paused by administrator.", level="WARNING")
        return {"status": "paused"}

    def resume(self):
        update_state({"status": "active"})
        append_log("GUARDIAN_STATE_CHANGE", "Guardian AI resumed to ACTIVE by administrator.", level="INFO")
        return {"status": "active"}

    def get_dashboard_data(self):
        """Aggregate telemetry for the Admin Control Center."""
        state = get_state()
        logs = get_recent_logs(limit=40)
        issues = list(get_all_issues().values())
        patches = list(get_all_patches().values())

        return {
            "state": state,
            "logs": logs,
            "issues": issues,
            "patches": patches
        }


guardian_service = GuardianAI()
