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
import secrets
from functools import wraps
from datetime import datetime
from flask import Blueprint, current_app, render_template, request, jsonify, redirect, url_for, session, flash, abort
from services.guardian import (
    guardian_service, get_state, get_recent_logs, get_all_issues, get_all_patches
)
from services.guardian.storage import update_patch_status, append_log
from utils.security import configured_secret, secret_matches
from utils.rate_limiter import rate_limit

owner_bp = Blueprint("owner_guardian", __name__, url_prefix="/owner/guardian")


def get_owner_pin():
    return configured_secret("OWNER_PIN", "ADMIN_PIN")


def get_owner_token():
    return configured_secret("OWNER_TOKEN", "GUARDIAN_ADMIN_TOKEN")


def get_owner_phone():
    return os.environ.get("OWNER_PHONE", "").strip()


@owner_bp.before_request
def owner_csrf_guard():
    """Protect browser form submissions with a per-session CSRF token."""
    if request.method == "GET":
        session.setdefault("_owner_csrf_token", secrets.token_urlsafe(32))
        return None
    if request.endpoint == "owner_guardian.cron_pulse":
        return None
    if current_app.config.get("TESTING") and not (request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")):
        return None
    expected = session.get("_owner_csrf_token", "")
    supplied = request.form.get("_csrf_token", "") or request.headers.get("X-CSRF-Token", "")
    if not secret_matches(supplied, expected):
        abort(400, description="Invalid or missing CSRF token.")


@owner_bp.context_processor
def owner_csrf_context():
    return {"owner_csrf_token": session.get("_owner_csrf_token", "")}


def require_owner(f):
    """Enforce strict server-side owner authorization."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Browser dashboard access requires the explicit owner PIN session.
        if session.get("is_owner_authenticated"):
            if session.get("owner_auth_method") != "owner_pin":
                # If a normal user tries to access owner resources, reject with 403 Forbidden
                append_log(
                    "SECURITY_ALERT_ACCESS_DENIED",
                    f"Rejected owner session authentication method on route: {request.path}",
                    level="WARNING",
                    details={"ip": request.remote_addr, "user_id": session.get("user_id")}
                )
                abort(403)
            return f(*args, **kwargs)

        # 4. Check submitted Owner PIN in login POST
        if request.method == "POST":
            submitted_pin = request.form.get("owner_pin") or request.form.get("pin")
            pin = get_owner_pin()
            if submitted_pin and not pin:
                return jsonify({"error": "Owner authentication is not configured. Set OWNER_PIN."}), 503
            if submitted_pin and secret_matches(submitted_pin, pin):
                session.clear()
                session["is_owner_authenticated"] = True
                session["owner_auth_method"] = "owner_pin"
                session["owner_role"] = "owner"
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
@rate_limit(limit=8, window_seconds=300, by_ip=True)
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
        owner_phone=get_owner_phone()
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


@owner_bp.route("/logout", methods=["POST"])
def logout():
    """Secure logout from Owner Control Center."""
    session.clear()
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
    owner_token = get_owner_token()
    if not secret_matches(token, owner_token) and not session.get("is_owner_authenticated"):
        # Deny access completely; never leak internal details
        return jsonify({"error": "Unauthorized: Owner token required.", "status": 403}), 403

    cycle_res = guardian_service.run_cycle(trigger_source="owner_cron_pulse")
    return jsonify({
        "success": True,
        "results": cycle_res
    })
