"""One-time, idempotent importer for legacy Guardian JSON backups.

Run only against a backed-up STAGING database:
  python scripts/import_guardian_json.py --backup-dir /secure/path/to/guardian_data

Expected files (all optional): guardian_state.json, guardian_logs.jsonl,
guardian_issues.json, guardian_patches.json. Source files are never modified.
"""
import argparse
import hashlib
import json
from pathlib import Path

from app import app
from extensions import db
from services.guardian.storage import (
    GuardianStateRecord, GuardianLogRecord, GuardianIssueRecord,
    GuardianPatchRecord,
)

FILES = (
    "guardian_state.json",
    "guardian_logs.jsonl",
    "guardian_issues.json",
    "guardian_patches.json",
)


class GuardianImportLedger(db.Model):
    __tablename__ = "guardian_import_ledger"
    bundle_sha256 = db.Column(db.String(64), primary_key=True)
    imported_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    counts_json = db.Column(db.Text, nullable=False)


def _read_bundle(folder: Path):
    bundle = {}
    digests = {}
    for filename in FILES:
        path = folder / filename
        if not path.exists():
            continue
        raw = path.read_bytes()
        digests[filename] = hashlib.sha256(raw).hexdigest()
        if filename.endswith(".jsonl"):
            rows = []
            for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{filename}:{line_no}: invalid JSON") from exc
                if not isinstance(item, dict):
                    raise ValueError(f"{filename}:{line_no}: expected JSON object")
                rows.append(item)
            bundle[filename] = rows
        else:
            try:
                item = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"{filename}: invalid UTF-8 JSON") from exc
            if filename == "guardian_state.json":
                if not isinstance(item, dict):
                    raise ValueError(f"{filename}: expected JSON object")
            elif not isinstance(item, dict):
                raise ValueError(f"{filename}: expected object keyed by record ID")
            bundle[filename] = item
    if not bundle:
        raise ValueError("No supported Guardian backup files found.")
    digest_input = json.dumps(digests, sort_keys=True, separators=(",", ":")).encode()
    return bundle, hashlib.sha256(digest_input).hexdigest()


def import_bundle(folder: Path):
    bundle, bundle_hash = _read_bundle(folder)
    with app.app_context():
        if db.session.get(GuardianImportLedger, bundle_hash):
            return {"status": "already_imported", "bundle_sha256": bundle_hash}

        counts = {"state": 0, "logs": 0, "issues": 0, "patches": 0}
        try:
            state = bundle.get("guardian_state.json")
            if state is not None and db.session.get(GuardianStateRecord, 1) is None:
                db.session.add(GuardianStateRecord(id=1, payload=json.dumps(state, ensure_ascii=False)))
                counts["state"] = 1

            for entry in bundle.get("guardian_logs.jsonl", []):
                required = ("event_type", "message")
                if any(not isinstance(entry.get(k), str) for k in required):
                    raise ValueError("guardian_logs.jsonl: each entry needs string event_type and message")
                created = entry.get("timestamp")
                try:
                    from datetime import datetime
                    created_at = datetime.fromisoformat(created) if created else datetime.utcnow()
                except (TypeError, ValueError) as exc:
                    raise ValueError("guardian_logs.jsonl: invalid timestamp") from exc
                db.session.add(GuardianLogRecord(
                    created_at=created_at,
                    level=str(entry.get("level", "INFO")).upper()[:16],
                    event_type=entry["event_type"][:80],
                    payload=json.dumps(entry, ensure_ascii=False),
                ))
                counts["logs"] += 1

            for issue_id, issue in bundle.get("guardian_issues.json", {}).items():
                if not isinstance(issue, dict):
                    raise ValueError(f"guardian_issues.json: {issue_id} must be an object")
                key = str(issue.get("id") or issue_id)
                if db.session.get(GuardianIssueRecord, key) is None:
                    detected = issue.get("detected_at")
                    from datetime import datetime
                    try:
                        detected_at = datetime.fromisoformat(detected) if detected else datetime.utcnow()
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"guardian_issues.json: invalid detected_at for {key}") from exc
                    db.session.add(GuardianIssueRecord(
                        issue_id=key, status=str(issue.get("status", "detected"))[:32],
                        severity=str(issue.get("severity", "unknown"))[:24],
                        detected_at=detected_at, payload=json.dumps(issue, ensure_ascii=False),
                    ))
                    counts["issues"] += 1

            for patch_id, patch in bundle.get("guardian_patches.json", {}).items():
                if not isinstance(patch, dict):
                    raise ValueError(f"guardian_patches.json: {patch_id} must be an object")
                key = str(patch.get("id") or patch_id)
                if db.session.get(GuardianPatchRecord, key) is None:
                    created = patch.get("created_at")
                    from datetime import datetime
                    try:
                        created_at = datetime.fromisoformat(created) if created else datetime.utcnow()
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"guardian_patches.json: invalid created_at for {key}") from exc
                    db.session.add(GuardianPatchRecord(
                        patch_id=key, status=str(patch.get("status", "pending_review"))[:32],
                        created_at=created_at, payload=json.dumps(patch, ensure_ascii=False),
                    ))
                    counts["patches"] += 1

            db.session.add(GuardianImportLedger(
                bundle_sha256=bundle_hash,
                counts_json=json.dumps(counts, sort_keys=True),
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return {"status": "imported", "bundle_sha256": bundle_hash, "counts": counts}


def main():
    parser = argparse.ArgumentParser(description="Import a legacy Guardian JSON backup into the configured database.")
    parser.add_argument("--backup-dir", required=True, help="Directory containing the legacy Guardian JSON backup files")
    parser.add_argument("--confirm-staging", action="store_true", help="Required acknowledgement that this is a backed-up staging database")
    args = parser.parse_args()
    if not args.confirm_staging:
        parser.error("Refusing to run without --confirm-staging.")
    result = import_bundle(Path(args.backup_dir).expanduser().resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
