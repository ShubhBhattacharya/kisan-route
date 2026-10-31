"""KisanRoute Guardian AI - Core Storage and Task Registry.

Manages persistent operational state, execution logs, issue tracking, and patch reviews
safely in JSON format or SQLite, fully compatible with both local and serverless runtimes.
"""

import os
import json
import time
from datetime import datetime

DATA_DIR = os.environ.get("GUARDIAN_DATA_DIR") or (
    "/tmp/guardian_data" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(__file__), "data")
)
os.makedirs(DATA_DIR, exist_ok=True)

STATE_FILE = os.path.join(DATA_DIR, "guardian_state.json")
LOGS_FILE = os.path.join(DATA_DIR, "guardian_logs.jsonl")
ISSUES_FILE = os.path.join(DATA_DIR, "guardian_issues.json")
PATCHES_FILE = os.path.join(DATA_DIR, "guardian_patches.json")


def _read_json(filepath, default=None):
    if default is None:
        default = {}
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(filepath, data):
    try:
        tmp_path = f"{filepath}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if os.path.exists(filepath):
            os.replace(tmp_path, filepath)
        else:
            os.rename(tmp_path, filepath)
    except Exception as e:
        print(f"[Guardian Storage] Write error for {filepath}: {e}")


def get_state():
    """Retrieve Guardian AI operational status and summary metrics."""
    default_state = {
        "status": "active",  # active, paused, maintenance
        "last_execution": None,
        "next_execution": None,
        "execution_count": 0,
        "uptime_percent": 100.0,
        "last_health_status": "healthy",
        "active_alerts_count": 0,
        "resolved_issues_count": 0,
        "pending_patches_count": 0,
        "total_cost_usd": 0.0,
        "quota_tokens_used": 0,
        "free_tier_provider": "google_gemini_free",
        "created_at": datetime.utcnow().isoformat()
    }
    state = _read_json(STATE_FILE, default_state)
    for k, v in default_state.items():
        if k not in state:
            state[k] = v
    return state


def update_state(updates: dict):
    state = get_state()
    state.update(updates)
    _write_json(STATE_FILE, state)
    return state


def append_log(event_type: str, message: str, level: str = "INFO", details: dict = None):
    """Log an operational event to the append-only logs."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "epoch": time.time(),
        "level": level.upper(),
        "event_type": event_type,
        "message": message,
        "details": details or {}
    }
    try:
        with open(LOGS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Guardian Log] Failed to write log: {e}")
    return entry


def get_recent_logs(limit: int = 100):
    """Return the most recent log entries up to `limit`."""
    if not os.path.exists(LOGS_FILE):
        return []
    lines = []
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
        parsed = []
        for l in reversed(lines[-limit:]):
            try:
                parsed.append(json.loads(l))
            except Exception:
                continue
        return parsed
    except Exception:
        return []


def record_issue(issue_id: str, title: str, category: str, severity: str, details: dict, tier: int = 1):
    """Register a detected problem."""
    issues = _read_json(ISSUES_FILE, {})
    issue = {
        "id": issue_id,
        "title": title,
        "category": category,  # frontend, backend, integration, security, workflow
        "severity": severity,  # low, medium, high, critical
        "tier": tier,          # 1=auto-safe, 2=patch-review, 3=manual-only
        "status": "detected",  # detected, analyzing, auto_fixed, patch_pending, resolved, rejected
        "detected_at": datetime.utcnow().isoformat(),
        "details": details,
        "resolution": None
    }
    issues[issue_id] = issue
    _write_json(ISSUES_FILE, issues)
    append_log("ISSUE_DETECTED", f"Issue [{category}] {title} (Tier {tier}, {severity})", level="WARNING", details=issue)
    return issue


def resolve_issue(issue_id: str, resolution_note: str, status: str = "resolved"):
    issues = _read_json(ISSUES_FILE, {})
    if issue_id in issues:
        issues[issue_id]["status"] = status
        issues[issue_id]["resolved_at"] = datetime.utcnow().isoformat()
        issues[issue_id]["resolution"] = resolution_note
        _write_json(ISSUES_FILE, issues)
        append_log("ISSUE_RESOLVED", f"Resolved issue {issue_id}: {resolution_note}", level="INFO")
        return issues[issue_id]
    return None


def get_all_issues():
    return _read_json(ISSUES_FILE, {})


def queue_patch(patch_id: str, issue_id: str, summary: str, diff_text: str, affected_files: list, tier: int = 2):
    """Queue a Tier 2 code patch for administrator review."""
    patches = _read_json(PATCHES_FILE, {})
    patch = {
        "id": patch_id,
        "issue_id": issue_id,
        "summary": summary,
        "diff_text": diff_text,
        "affected_files": affected_files,
        "tier": tier,
        "status": "pending_review",  # pending_review, approved, rejected, applied, rolled_back
        "created_at": datetime.utcnow().isoformat(),
        "review_notes": None
    }
    patches[patch_id] = patch
    _write_json(PATCHES_FILE, patches)
    append_log("PATCH_QUEUED", f"Patch queued for review: {summary} ({patch_id})", level="INFO", details=patch)
    return patch


def get_all_patches():
    return _read_json(PATCHES_FILE, {})


def update_patch_status(patch_id: str, status: str, notes: str = ""):
    patches = _read_json(PATCHES_FILE, {})
    if patch_id in patches:
        patches[patch_id]["status"] = status
        patches[patch_id]["reviewed_at"] = datetime.utcnow().isoformat()
        patches[patch_id]["review_notes"] = notes
        _write_json(PATCHES_FILE, patches)
        append_log("PATCH_STATUS_CHANGED", f"Patch {patch_id} status changed to {status}: {notes}", level="INFO")
        return patches[patch_id]
    return None
