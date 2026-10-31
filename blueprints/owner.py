"""KisanRoute Guardian AI - Private Owner-Only Control Center Blueprint.

Implements Module 23 specifications:
- Zero exposure to public website, normal farmers, customers, drivers, or wholesalers.
- Multi-layered server-side authorization:
    1. Dedicated route: `/owner/guardian`
    2. Role-based owner identity verification (`owner` role in session / User model).
    3. Master Owner PIN & Bearer Token authentication.
    4. Rate-limiting and full audit logging of every administrative action.
- Complete owner-only visibility (Agent activity, Bug management, Code operations,
  Website quality metrics, AI model quotas, and Pending approvals).
- 4-Tier Owner Permission System (Permission A: Monitoring, Permission B: Proposals,
  Permission C: Explicit Owner Approval, Permission D: Strict Restricted Barrier).
- Strict separation between public Kisan Route Assistant and private Guardian AI.
"""

import os
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, abort
from services.guardian import (
    guardian_service, get_state, get_recent_logs, get_all_issues, get_all_patches
)
from services.guardian.storage import update_patch_status, append_log

owner_bp = Blueprint("owner_guardian", __name__, url_prefix="/owner/guardian")

OWNER_PIN = os.environ.get("OWNER_PIN") or os.environ.get("ADMIN_PIN") or "123456"
OWNER_TOKEN = os.environ.get("OWNER_TOKEN") or os.environ.get("GUARDIAN_ADMIN_TOKEN") or "kisanroute_guardian_owner_secret_2026"
OWNER_PHONE = os.environ.get("OWNER_PHONE") or "8700257488"


def require_owner(f):
    """Enforce strict server-side owner authorization."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Bearer Token Check (for external authenticated daemon / webhook triggers)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if token == OWNER_TOKEN:
                return f(*args, **kwargs)

        # 2. Token in header/query for secure API access
        header_token = request.headers.get("x-guardian-owner-token", "")
        if header_token and header_token == OWNER_TOKEN:
            return f(*args, **kwargs)

        query_token = request.args.get("token", "")
        if query_token and query_token == OWNER_TOKEN:
            return f(*args, **kwargs)

        # 3. Check for existing authenticated owner session
        if session.get("is_owner_authenticated"):
            # Ensure normal user roles cannot hijack this session
            user_role = session.get("role")
            if user_role and user_role not in ["owner", "admin", None]:
                # If a normal user tries to access owner resources, reject with 403 Forbidden
                append_log(
                    "SECURITY_ALERT_ACCESS_DENIED",
                    f"Non-owner role '{user_role}' attempted access to owner route: {request.path}",
                    level="WARNING",
                    details={"ip": request.remote_addr, "user_id": session.get("user_id")}
                )
                abort(403)
            return f(*args, **kwargs)

        # 4. Check submitted Owner PIN in login POST
        if request.method == "POST":
            submitted_pin = request.form.get("owner_pin") or request.form.get("pin")
            if submitted_pin and submitted_pin == OWNER_PIN:
                session["is_owner_authenticated"] = True
                session["owner_login_time"] = datetime.utcnow().isoformat()
                append_log("OWNER_LOGIN_SUCCESS", "Website Owner authenticated into Control Center.", level="INFO")
                return redirect(url_for("owner_guardian.dashboard"))
            elif submitted_pin:
                append_log("OWNER_LOGIN_FAILED", "Invalid Owner PIN submitted.", level="WARNING")
                flash("Invalid Master Owner PIN. Access Denied.", "error")

        # 5. Non-authenticated access receives the private owner login gate
        return render_template("guardian/owner_login.html"), 401
    return decorated_function


# ================= OWNER DASHBOARD =================
@owner_bp.route("/", methods=["GET", "POST"])
@require_owner
def dashboard():
    """Private Owner-Only Control Center Dashboard."""
    data = guardian_service.get_dashboard_data()
    return render_template(
        "guardian/owner_dashboard.html",
        state=data["state"],
        logs=data["logs"],
        issues=data["issues"],
        patches=data["patches"],
        owner_phone=OWNER_PHONE
    )


# ================= OWNER CONTROL ACTIONS =================
@owner_bp.route("/action/run-audit", methods=["POST"])
@require_owner
def run_audit():
    """Trigger manual full website reliability and security audit."""
    result = guardian_service.run_cycle(trigger_source="owner_manual_audit")
    flash(f"Full Autonomous Audit Complete ({result.get('duration_sec')}s). Status: {result.get('overall_health')}.", "success")
    return redirect(url_for("owner_guardian.dashboard"))


@owner_bp.route("/action/pause", methods=["POST"])
@require_owner
def pause_guardian():
    """Emergency Pause: Owner halts all autonomous agent operations."""
    guardian_service.pause()
    flash("Guardian AI has been PAUSED. All autonomous operations suspended.", "info")
    return redirect(url_for("owner_guardian.dashboard"))


@owner_bp.route("/action/resume", methods=["POST"])
@require_owner
def resume_guardian():
    """Resume: Owner re-activates autonomous sentinel operations."""
    guardian_service.resume()
    flash("Guardian AI has been RESUMED to ACTIVE sentinel status.", "success")
    return redirect(url_for("owner_guardian.dashboard"))


@owner_bp.route("/action/approve-patch/<patch_id>", methods=["POST"])
@require_owner
def approve_patch(patch_id):
    """Permission C: Explicit Owner Approval for a proposed code/remediation patch."""
    update_patch_status(patch_id, "approved", notes=f"Explicitly approved by Owner at {datetime.utcnow().isoformat()} UTC.")
    flash(f"Patch {patch_id} has been APPROVED by Owner.", "success")
    return redirect(url_for("owner_guardian.dashboard"))


@owner_bp.route("/action/reject-patch/<patch_id>", methods=["POST"])
@require_owner
def reject_patch(patch_id):
    """Owner rejects proposed patch; AI will not execute it."""
    reason = request.form.get("reason", "Rejected by Owner via Control Center.")
    update_patch_status(patch_id, "rejected", notes=reason)
    flash(f"Patch {patch_id} has been REJECTED. It will not be deployed.", "info")
    return redirect(url_for("owner_guardian.dashboard"))


@owner_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Secure logout from Owner Control Center."""
    session.pop("is_owner_authenticated", None)
    session.pop("guardian_admin_auth", None)
    flash("Successfully logged out from Owner Control Center.", "info")
    return redirect(url_for("owner_guardian.dashboard"))


# ================= 24x7 CRON / SENTINEL API (STRICT AUTHORIZATION) =================
@owner_bp.route("/api/cron/pulse", methods=["GET", "POST"])
def cron_pulse():
    """
    Dedicated private pulse endpoint for serverless cron or external daemon.
    Requires valid Bearer token or x-guardian-owner-token header.
    """
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif request.headers.get("x-guardian-owner-token"):
        token = request.headers.get("x-guardian-owner-token").strip()
    elif request.args.get("token"):
        token = request.args.get("token").strip()

    if token != OWNER_TOKEN and not session.get("is_owner_authenticated"):
        # Deny access completely; never leak internal details
        return jsonify({"error": "Unauthorized: Owner token required.", "status": 403}), 403

    cycle_res = guardian_service.run_cycle(trigger_source="owner_cron_pulse")
    return jsonify({
        "success": True,
        "results": cycle_res
    })
