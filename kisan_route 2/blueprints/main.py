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


@main_bp.route("/api/weather")
def api_weather():
    from utils.weather import get_agri_weather
    lat = request.args.get("lat", type=float) or 28.14
    lon = request.args.get("lon", type=float) or 77.32
    return jsonify(get_agri_weather(lat=lat, lon=lon))


@main_bp.route("/api/notifications")
def api_notifications():
    from utils.weather import get_agri_weather
    w = get_agri_weather()
    alerts = [
        {
            "id": 1,
            "category": "mandi",
            "icon": "📊",
            "title": "मंडी भाव में तेजी",
            "body": "पलवल व आज़ादपुर मंडी में गेहूं ₹2,250 और टमाटर ₹22/किलो पर पहुंचा।",
            "time": "10 मिनट पहले",
            "url": "/farmer/mandi-rates"
        },
        {
            "id": 2,
            "category": "weather",
            "icon": w.get("icon", "🌦️"),
            "title": "कृषि मौसम अलर्ट (" + str(w.get("temp", 31)) + "°C)",
            "body": w.get("advisory_hi", "मौसम साफ है। फसल कटाई व परिवहन के लिए अनुकूल समय है।"),
            "time": "अभी-अभी",
            "url": "/farmer/dashboard"
        },
        {
            "id": 3,
            "category": "logistics",
            "icon": "🚚",
            "title": "साझा ट्रक लोड उपलब्ध",
            "body": "एनसीआर रूट पर 2 खाली कमर्शियल गाड़ियां उपलब्ध हैं। 40% तक भाड़ा बचाएं।",
            "time": "35 मिनट पहले",
            "url": "/driver/dashboard"
        },
        {
            "id": 4,
            "category": "order",
            "icon": "🛒",
            "title": "ताज़ा फसल आर्डर",
            "body": "ग्राहक ने 50 किलो गेहूं का नया आर्डर बुक किया है।",
            "time": "1 घंटा पहले",
            "url": "/customer/dashboard"
        }
    ]
    return jsonify({"success": True, "count": len(alerts), "notifications": alerts})


@main_bp.route("/manifest.json")
def manifest():
    return send_from_directory(current_app.static_folder, "manifest.json", mimetype="application/manifest+json")


@main_bp.route("/sw.js")
def service_worker():
    response = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

