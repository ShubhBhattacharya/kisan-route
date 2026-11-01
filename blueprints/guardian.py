"""KisanRoute Guardian AI - Protected Blueprint & API Endpoints.

Provides the secure administrative dashboard, execution endpoints, and webhook triggers
protected by session PIN / Admin key to prevent unauthorized access.
"""

import os
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from services.guardian import guardian_service, get_state, get_recent_logs, get_all_issues, get_all_patches
from services.guardian.storage import update_patch_status
from utils.security import configured_secret, secret_matches

guardian_bp = Blueprint("guardian", __name__, url_prefix="/admin/guardian")

ADMIN_PIN = configured_secret("ADMIN_PIN", "OWNER_PIN")
ADMIN_TOKEN = configured_secret("GUARDIAN_ADMIN_TOKEN", "OWNER_TOKEN")


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Bearer Token Check (for automated external cron / scripts)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if secret_matches(token, ADMIN_TOKEN):
                return f(*args, **kwargs)

        # 3. Session PIN Auth Check
        if session.get("guardian_admin_auth"):
            return f(*args, **kwargs)

        # Check submitted PIN in form/query
        submitted_pin = request.form.get("pin")
        if submitted_pin and not ADMIN_PIN:
            return jsonify({"error": "Guardian admin authentication is not configured."}), 503
        if submitted_pin and secret_matches(submitted_pin, ADMIN_PIN):
            session.clear()
            session["guardian_admin_auth"] = True
            return f(*args, **kwargs)

        # Render PIN gate if not authorized
        return render_template("guardian/login.html")
    return decorated_function


@guardian_bp.route("/", methods=["GET", "POST"])
@require_admin
def dashboard():
    data = guardian_service.get_dashboard_data()
    return render_template(
        "guardian/dashboard.html",
        state=data["state"],
        logs=data["logs"],
        issues=data["issues"],
        patches=data["patches"]
    )


@guardian_bp.route("/action/run-cycle", methods=["POST"])
@require_admin
def run_cycle():
    result = guardian_service.run_cycle(trigger_source="admin_dashboard")
    flash(f"Full Audit complete in {result.get('duration_sec')}s. Health: {result.get('overall_health')}", "success")
    return redirect(url_for("guardian.dashboard"))


@guardian_bp.route("/action/pause", methods=["POST"])
@require_admin
def pause_guardian():
    guardian_service.pause()
    flash("Guardian AI has been PAUSED.", "info")
    return redirect(url_for("guardian.dashboard"))


@guardian_bp.route("/action/resume", methods=["POST"])
@require_admin
def resume_guardian():
    guardian_service.resume()
    flash("Guardian AI has been RESUMED to active status.", "success")
    return redirect(url_for("guardian.dashboard"))


@guardian_bp.route("/action/approve-patch/<patch_id>", methods=["POST"])
@require_admin
def approve_patch(patch_id):
    update_patch_status(patch_id, "approved", notes="Approved via Admin Control Center.")
    flash(f"Patch {patch_id} approved for deployment.", "success")
    return redirect(url_for("guardian.dashboard"))


@guardian_bp.route("/action/reject-patch/<patch_id>", methods=["POST"])
@require_admin
def reject_patch(patch_id):
    update_patch_status(patch_id, "rejected", notes="Rejected by administrator.")
    flash(f"Patch {patch_id} rejected.", "info")
    return redirect(url_for("guardian.dashboard"))


# ================= 24x7 AUTOMATED CRON WEBHOOK =================
@guardian_bp.route("/cron/health", methods=["GET", "POST"])
def cron_health():
    """Triggered by Vercel Cron, external monitoring cron, or background workers."""
    auth_key = request.headers.get("x-guardian-token", "")
    if not secret_matches(auth_key, ADMIN_TOKEN) and not session.get("guardian_admin_auth"):
        return jsonify({"status": "ok"}), 200

    # Authorized: run complete inspection cycle
    cycle_res = guardian_service.run_cycle(trigger_source="cron_trigger")
    return jsonify({
        "success": True,
        "cycle_results": cycle_res
    })
