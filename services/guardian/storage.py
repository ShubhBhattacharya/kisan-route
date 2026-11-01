"""Durable Guardian storage backed by the application's SQLAlchemy database.

All Guardian state, logs, issues and patch reviews are stored in relational tables.
There is deliberately no filesystem or /tmp fallback: database errors are surfaced.
"""
import json
import time
from datetime import datetime

from extensions import db


class GuardianStateRecord(db.Model):
    __tablename__ = "guardian_state"
    id = db.Column(db.Integer, primary_key=True, default=1)
    payload = db.Column(db.Text, nullable=False)


class GuardianLogRecord(db.Model):
    __tablename__ = "guardian_logs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    level = db.Column(db.String(16), nullable=False, index=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    payload = db.Column(db.Text, nullable=False)


class GuardianIssueRecord(db.Model):
    __tablename__ = "guardian_issues"
    issue_id = db.Column(db.String(120), primary_key=True)
    status = db.Column(db.String(32), nullable=False, index=True)
    severity = db.Column(db.String(24), nullable=False, index=True)
    detected_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    payload = db.Column(db.Text, nullable=False)


class GuardianPatchRecord(db.Model):
    __tablename__ = "guardian_patches"
    patch_id = db.Column(db.String(120), primary_key=True)
    status = db.Column(db.String(32), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    payload = db.Column(db.Text, nullable=False)

class GuardianWorkerHeartbeat(db.Model):
    __tablename__ = "guardian_worker_heartbeats"
    worker_id = db.Column(db.String(120), primary_key=True)
    last_seen_at = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(24), nullable=False)
    last_cycle_at = db.Column(db.DateTime, nullable=True)
    details = db.Column(db.Text, nullable=False, default="{}")


def record_worker_heartbeat(worker_id: str, status: str = "running", last_cycle_at=None, details=None):
    now = _utcnow()
    row = db.session.get(GuardianWorkerHeartbeat, worker_id)
    if row is None:
        row = GuardianWorkerHeartbeat(worker_id=worker_id, last_seen_at=now,
                                      status=status, last_cycle_at=last_cycle_at,
                                      details=_dump(details or {}))
        db.session.add(row)
    else:
        row.last_seen_at = now
        row.status = status
        if last_cycle_at is not None:
            row.last_cycle_at = last_cycle_at
        row.details = _dump(details or {})
    db.session.commit()
    return row


def get_worker_health(stale_after_seconds: int = 300):
    rows = GuardianWorkerHeartbeat.query.all()
    if not rows:
        return {"status": "not_configured", "workers": [], "checked_at": _utcnow().isoformat()}
    now = _utcnow()
    workers = []
    for row in rows:
        age = max(0, int((now - row.last_seen_at).total_seconds()))
        workers.append({
            "worker_id": row.worker_id,
            "status": row.status if age <= stale_after_seconds else "stale",
            "last_seen_at": row.last_seen_at.isoformat(),
            "last_cycle_at": row.last_cycle_at.isoformat() if row.last_cycle_at else None,
            "age_seconds": age,
        })
    overall = "active" if any(w["status"] == "running" for w in workers) else "offline"
    return {"status": overall, "workers": workers, "checked_at": now.isoformat()}


def _dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value):
    return json.loads(value)


def _utcnow():
    return datetime.utcnow()


def get_state():
    """Read the singleton state row; absent row means unconfigured, not healthy."""
    default = {
        "status": "not_configured",
        "last_execution": None,
        "next_execution": None,
        "execution_count": 0,
        "uptime_percent": 0.0,
        "last_health_status": "unknown",
        "active_alerts_count": 0,
        "resolved_issues_count": 0,
        "pending_patches_count": 0,
        "total_cost_usd": None,
        "quota_tokens_used": 0,
        "free_tier_provider": "not_configured",
        "created_at": _utcnow().isoformat(),
    }
    row = db.session.get(GuardianStateRecord, 1)
    if row is None:
        return default
    state = _load(row.payload)
    for key, value in default.items():
        state.setdefault(key, value)
    return state


def update_state(updates: dict):
    row = db.session.get(GuardianStateRecord, 1)
    state = get_state()
    state.update(updates)
    if row is None:
        row = GuardianStateRecord(id=1, payload=_dump(state))
        db.session.add(row)
    else:
        row.payload = _dump(state)
    db.session.commit()
    return state


def append_log(event_type: str, message: str, level: str = "INFO", details: dict = None):
    entry = {
        "timestamp": _utcnow().isoformat(),
        "epoch": time.time(),
        "level": level.upper(),
        "event_type": event_type,
        "message": message,
        "details": details or {},
    }
    db.session.add(GuardianLogRecord(
        created_at=_utcnow(),
        level=entry["level"],
        event_type=event_type,
        payload=_dump(entry),
    ))
    db.session.commit()
    return entry


def get_recent_logs(limit: int = 100):
    safe_limit = max(1, min(int(limit), 1000))
    rows = (GuardianLogRecord.query
            .order_by(GuardianLogRecord.id.desc())
            .limit(safe_limit)
            .all())
    return [_load(row.payload) for row in rows]


def record_issue(issue_id: str, title: str, category: str, severity: str,
                 details: dict, tier: int = 1):
    issue = {
        "id": issue_id,
        "title": title,
        "category": category,
        "severity": severity,
        "tier": tier,
        "status": "detected",
        "detected_at": _utcnow().isoformat(),
        "details": details,
        "resolution": None,
    }
    row = db.session.get(GuardianIssueRecord, issue_id)
    if row is None:
        row = GuardianIssueRecord(issue_id=issue_id, status="detected",
                                  severity=severity, detected_at=_utcnow(),
                                  payload=_dump(issue))
        db.session.add(row)
    else:
        row.status = "detected"
        row.severity = severity
        row.payload = _dump(issue)
    db.session.commit()
    append_log("ISSUE_DETECTED", f"Issue [{category}] {title} (Tier {tier}, {severity})",
               level="WARNING", details=issue)
    return issue


def resolve_issue(issue_id: str, resolution_note: str, status: str = "resolved"):
    row = db.session.get(GuardianIssueRecord, issue_id)
    if row is None:
        return None
    issue = _load(row.payload)
    issue["status"] = status
    issue["resolved_at"] = _utcnow().isoformat()
    issue["resolution"] = resolution_note
    row.status = status
    row.payload = _dump(issue)
    db.session.commit()
    append_log("ISSUE_RESOLVED", f"Resolved issue {issue_id}: {resolution_note}")
    return issue


def get_all_issues():
    rows = GuardianIssueRecord.query.order_by(GuardianIssueRecord.detected_at.desc()).all()
    return {row.issue_id: _load(row.payload) for row in rows}


def queue_patch(patch_id: str, issue_id: str, summary: str, diff_text: str,
                affected_files: list, tier: int = 2):
    patch = {
        "id": patch_id,
        "issue_id": issue_id,
        "summary": summary,
        "diff_text": diff_text,
        "affected_files": affected_files,
        "tier": tier,
        "status": "pending_review",
        "created_at": _utcnow().isoformat(),
        "review_notes": None,
    }
    row = db.session.get(GuardianPatchRecord, patch_id)
    if row is None:
        row = GuardianPatchRecord(patch_id=patch_id, status="pending_review",
                                  created_at=_utcnow(), payload=_dump(patch))
        db.session.add(row)
    else:
        row.status = "pending_review"
        row.payload = _dump(patch)
    db.session.commit()
    append_log("PATCH_QUEUED", f"Patch queued for review: {summary} ({patch_id})")
    return patch


def get_all_patches():
    rows = GuardianPatchRecord.query.order_by(GuardianPatchRecord.created_at.desc()).all()
    return {row.patch_id: _load(row.payload) for row in rows}


def update_patch_status(patch_id: str, status: str, notes: str = ""):
    row = db.session.get(GuardianPatchRecord, patch_id)
    if row is None:
        return None
    patch = _load(row.payload)
    patch["status"] = status
    patch["reviewed_at"] = _utcnow().isoformat()
    patch["review_notes"] = notes
    row.status = status
    row.payload = _dump(patch)
    db.session.commit()
    append_log("PATCH_STATUS_CHANGED", f"Patch {patch_id} status changed to {status}: {notes}")
    return patch
