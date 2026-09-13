import os
from flask import Blueprint, jsonify, render_template, request, session, url_for, redirect, send_from_directory, current_app, flash

from translations.strings import LANGUAGES
from utils.chatbot import get_prompts, get_response

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/index.html")
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


@main_bp.route("/api/news")
def api_news():
    from utils.news import get_agri_news
    category = request.args.get("category")
    return jsonify({"success": True, "news": get_agri_news(category=category)})


@main_bp.route("/api/notifications")
def api_notifications():
    from utils.weather import get_agri_weather
    lang = request.args.get("lang") or session.get("lang", "en")
    w = get_agri_weather()
    
    alerts_data = [
        {
            "id": 1,
            "category": "mandi",
            "icon": "📊",
            "title_hi": "मंडी भाव अपडेट",
            "title_en": "Mandi Price Surge",
            "body_hi": "पलवल व आज़ादपुर मंडी में गेहूं ₹2,250 और टमाटर ₹22/किलो पर पहुंचा।",
            "body_en": "Wheat reached ₹2,250/qtl and Tomato at ₹22/kg in Palwal & Azadpur Mandis.",
            "time_hi": "10 मिनट पहले",
            "time_en": "10 mins ago",
            "url": "/farmer/mandi-rates"
        },
        {
            "id": 2,
            "category": "weather",
            "icon": w.get("icon", "🌦️"),
            "title_hi": f"मौसम परामर्श ({w.get('temp', 31)}°C)",
            "title_en": f"Agri Weather Advisory ({w.get('temp', 31)}°C)",
            "body_hi": w.get("advisory_hi", "मौसम साफ है। फसल कटाई व परिवहन के लिए अनुकूल समय है।"),
            "body_en": w.get("advisory_en", "Clear skies. Ideal conditions for harvesting and transit."),
            "time_hi": "ताज़ा अपडेट",
            "time_en": "Just now",
            "url": "/farmer/dashboard"
        },
        {
            "id": 3,
            "category": "logistics",
            "icon": "🚚",
            "title_hi": "साझा ट्रक लोड उपलब्ध",
            "title_en": "Shared Truck Load Available",
            "body_hi": "एनसीआर रूट पर 2 खाली कमर्शियल गाड़ियां उपलब्ध हैं। 40% तक भाड़ा बचाएं।",
            "body_en": "2 commercial vehicles with shared capacity available on NCR route. Save up to 40% freight.",
            "time_hi": "35 मिनट पहले",
            "time_en": "35 mins ago",
            "url": "/driver/dashboard"
        },
        {
            "id": 4,
            "category": "order",
            "icon": "🛒",
            "title_hi": "ताज़ा फसल आर्डर",
            "title_en": "Fresh Produce Order",
            "body_hi": "ग्राहक ने 50 किलो गेहूं का नया आर्डर बुक किया है।",
            "body_en": "Buyer booked a new order for 50 kg farm wheat.",
            "time_hi": "1 घंटा पहले",
            "time_en": "1 hour ago",
            "url": "/customer/dashboard"
        }
    ]

    is_hi = (lang == "hi")
    alerts = []
    for a in alerts_data:
        alerts.append({
            "id": a["id"],
            "category": a["category"],
            "icon": a["icon"],
            "title": a["title_hi"] if is_hi else a["title_en"],
            "body": a["body_hi"] if is_hi else a["body_en"],
            "time": a["time_hi"] if is_hi else a["time_en"],
            "title_hi": a["title_hi"],
            "title_en": a["title_en"],
            "body_hi": a["body_hi"],
            "body_en": a["body_en"],
            "time_hi": a["time_hi"],
            "time_en": a["time_en"],
            "url": a["url"]
        })

    return jsonify({"success": True, "count": len(alerts), "lang": lang, "notifications": alerts})


@main_bp.route("/manifest.json")
def manifest():
    public_dir = os.path.join(current_app.root_path, "public")
    if os.path.exists(os.path.join(public_dir, "manifest.json")):
        return send_from_directory(public_dir, "manifest.json", mimetype="application/manifest+json")
    return send_from_directory(current_app.static_folder, "manifest.json", mimetype="application/manifest+json")


@main_bp.route("/icon-192.png")
def icon_192():
    public_dir = os.path.join(current_app.root_path, "public")
    if os.path.exists(os.path.join(public_dir, "icon-192.png")):
        return send_from_directory(public_dir, "icon-192.png", mimetype="image/png")
    return send_from_directory(os.path.join(current_app.static_folder, "images", "icons"), "icon-192.png", mimetype="image/png")


@main_bp.route("/icon-512.png")
def icon_512():
    public_dir = os.path.join(current_app.root_path, "public")
    if os.path.exists(os.path.join(public_dir, "icon-512.png")):
        return send_from_directory(public_dir, "icon-512.png", mimetype="image/png")
    return send_from_directory(os.path.join(current_app.static_folder, "images", "icons"), "icon-512.png", mimetype="image/png")


@main_bp.route("/sw.js")
def service_worker():
    response = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ================= MAINTENANCE MODE CONTROL API & BYPASS =================
@main_bp.route("/maintenance/on")
def maintenance_on():
    from utils.maintenance import set_maintenance_mode, is_bypass_authorized
    key = request.args.get("key", "")
    if is_bypass_authorized(key):
        set_maintenance_mode(True)
        return jsonify({"success": True, "maintenance": True, "message": "Maintenance mode is now ACTIVE."})
    return jsonify({"success": False, "error": "Unauthorized"}), 401


@main_bp.route("/maintenance/off")
def maintenance_off():
    from utils.maintenance import set_maintenance_mode, is_bypass_authorized
    key = request.args.get("key", "")
    if is_bypass_authorized(key):
        set_maintenance_mode(False)
        return jsonify({"success": True, "maintenance": False, "message": "Maintenance mode is now DEACTIVATED. Site is live."})
    return jsonify({"success": False, "error": "Unauthorized"}), 401


@main_bp.route("/maintenance/status")
def maintenance_status():
    from utils.maintenance import is_maintenance_mode
    return jsonify({
        "success": True,
        "maintenance_mode": is_maintenance_mode(),
        "bypass_active": bool(session.get("maintenance_bypass"))
    })


@main_bp.route("/maintenance/bypass", methods=["GET", "POST"])
def maintenance_bypass():
    from utils.maintenance import is_bypass_authorized
    if request.method == "POST":
        pin = request.form.get("pin", "")
        if is_bypass_authorized(pin):
            session["maintenance_bypass"] = True
            flash("Admin bypass activated! You can now access the full site during maintenance.", "info")
            return redirect(url_for("main.home"))
        flash("Invalid Admin PIN.", "error")
        return redirect(url_for("main.home"))

    key = request.args.get("key", "")
    if is_bypass_authorized(key):
        session["maintenance_bypass"] = True
        flash("Admin bypass activated!", "info")
        return redirect(url_for("main.home"))
    return redirect(url_for("main.home"))


