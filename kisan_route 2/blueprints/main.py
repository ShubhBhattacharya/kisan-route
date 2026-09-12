from flask import Blueprint, jsonify, render_template, request, session, url_for, redirect, send_from_directory, current_app

from translations.strings import LANGUAGES
from utils.chatbot import get_prompts, get_response

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("home.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/set-language/<lang_code>")
def set_language(lang_code):
    valid_codes = {code for code, _label in LANGUAGES}
    if lang_code in valid_codes:
        session["lang"] = lang_code
    next_url = request.referrer or url_for("main.home")
    return redirect(next_url)


@main_bp.route("/api/chatbot/prompts")
def chatbot_prompts():
    role = session.get("role") or "default"
    return jsonify({"role": role, "prompts": get_prompts(role)})


@main_bp.route("/api/chatbot/ask", methods=["POST"])
def chatbot_ask():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "")
    return jsonify({"reply": get_response(message)})


@main_bp.route("/manifest.json")
def manifest():
    return send_from_directory(current_app.static_folder, "manifest.json", mimetype="application/manifest+json")


@main_bp.route("/sw.js")
def service_worker():
    response = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response
