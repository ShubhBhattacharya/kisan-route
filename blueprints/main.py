import os
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, session, url_for, redirect, send_from_directory, current_app, flash
from werkzeug.security import generate_password_hash

from config import Config
from models import db, User
from translations.strings import LANGUAGES
from utils.auth import clean_phone
from utils.chatbot import get_prompts, get_response
from utils.supabase_client import supabase

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


@main_bp.route("/api/voice/process", methods=["POST"])
def api_voice_process():
    from utils.voice import process_voice_query
    payload = request.get_json(silent=True) or {}
    query = payload.get("query", "").strip()
    lang = payload.get("lang", "hi-IN")
    role = session.get("role") or payload.get("role") or "default"
    result = process_voice_query(query, lang_hint=lang, role=role)
    return jsonify(result)


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


@main_bp.route("/api/send-otp", methods=["POST"])
def send_otp():
    """Send SMS OTP using Fast2SMS Quick OTP API via GET/POST."""
    payload = request.get_json(silent=True) or {}
    phone_raw = payload.get("phone", "")
    otp = str(payload.get("otp", "")).strip()

    if not phone_raw or not otp:
        return jsonify({"success": False, "message": "Both phone and otp parameters are required."}), 400

    # Clean phone: strip non-digits, leading zeros, country code 91
    phone_10 = clean_phone(phone_raw)
    if len(phone_10) != 10 or not phone_10.isdigit():
        return jsonify({
            "success": False,
            "message": "Invalid phone number format. Strictly a 10-digit Indian mobile number is required (e.g. 8700257488)."
        }), 400

    if not (4 <= len(otp) <= 6) or not otp.isdigit():
        return jsonify({"success": False, "message": "Invalid OTP format. 4 to 6 numeric digits required."}), 400

    api_key = (
        getattr(Config, "FAST2SMS_API_KEY", "")
        or os.environ.get("FAST2SMS_API_KEY")
        or os.environ.get("SMS_API_KEY", "")
    ).strip()

    if not api_key:
        return jsonify({
            "success": False,
            "message": "FAST2SMS_API_KEY is not configured in server environment."
        }), 500

    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    message_text = f"Your KisanRoute verification code is: {otp}"
    params = urllib.parse.urlencode({
        "authorization": api_key,
        "route": "q",
        "message": message_text,
        "language": "english",
        "flash": "0",
        "numbers": phone_10
    })
    get_url = f"https://www.fast2sms.com/dev/bulkV2?{params}"

    # Try GET request first
    try:
        req = urllib.request.Request(
            get_url,
            headers={
                "authorization": api_key,
                "cache-control": "no-cache",
                "User-Agent": "KisanRoute/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and data.get("return") is True:
                return jsonify({
                    "success": True,
                    "message": "OTP sent successfully via Fast2SMS Quick SMS.",
                    "request_id": data.get("request_id")
                })
            else:
                msg = data.get("message")
                err_text = ", ".join(msg) if isinstance(msg, list) else str(msg or "Failed to send OTP via Fast2SMS.")
                return jsonify({"success": False, "message": err_text, "fast2sms_response": data}), 400
    except urllib.error.HTTPError as he:
        # Read the exact error response body from Fast2SMS
        raw_error = he.read().decode("utf-8", errors="replace")
        current_app.logger.error(f"[Fast2SMS HTTPError {he.code}] Response: {raw_error}")
        print(f"[Fast2SMS HTTPError {he.code}] Response: {raw_error}")

        # Try POST method fallback with JSON body
        try:
            post_body = json.dumps({
                "route": "q",
                "message": message_text,
                "language": "english",
                "flash": 0,
                "numbers": phone_10
            }).encode("utf-8")

            post_req = urllib.request.Request(
                "https://www.fast2sms.com/dev/bulkV2",
                data=post_body,
                headers={
                    "authorization": api_key,
                    "Content-Type": "application/json",
                    "cache-control": "no-cache",
                    "User-Agent": "KisanRoute/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(post_req, timeout=10.0) as post_resp:
                post_data = json.loads(post_resp.read().decode("utf-8"))
                if post_data and post_data.get("return") is True:
                    return jsonify({
                        "success": True,
                        "message": "OTP sent successfully via Fast2SMS.",
                        "request_id": post_data.get("request_id")
                    })
        except urllib.error.HTTPError as post_he:
            post_err_body = post_he.read().decode("utf-8", errors="replace")
            print(f"[Fast2SMS POST HTTPError {post_he.code}] Response: {post_err_body}")
            raw_error = post_err_body

        try:
            err_json = json.loads(raw_error)
            err_msg = err_json.get("message")
            if isinstance(err_msg, list):
                err_msg = ", ".join(err_msg)
            else:
                err_msg = str(err_msg or raw_error)
        except Exception:
            err_msg = raw_error or "Fast2SMS returned HTTP Error 400."

        return jsonify({
            "success": False,
            "message": f"Fast2SMS error: {err_msg}",
            "raw_response": raw_error
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Network error communicating with Fast2SMS: {str(e)}"
        }), 502


@main_bp.route("/api/auth/phone-login", methods=["POST"])
@main_bp.route("/api/auth/firebase-login", methods=["POST"])
def phone_login():
    """Verify phone authentication, create or restore user session in Supabase
    users/profiles tables, persist local database user, and establish platform session.
    """
    payload = request.get_json(silent=True) or {}
    phone_raw = payload.get("phone", "")
    role = (payload.get("role") or "farmer").lower().strip()
    full_name = (payload.get("full_name") or "").strip()
    uid = payload.get("uid", "")

    valid_roles = {"farmer", "driver", "cluster", "customer", "wholesaler"}
    if role not in valid_roles:
        role = "farmer"

    if not phone_raw:
        return jsonify({"success": False, "error": "Phone number is required."}), 400

    # Normalize phone: extract last 10 digits
    cleaned = clean_phone(phone_raw)
    phone_10 = cleaned[-10:] if len(cleaned) >= 10 else cleaned
    if len(phone_10) != 10 or not phone_10.isdigit():
        return jsonify({"success": False, "error": "Invalid Indian phone number format. 10 numeric digits required."}), 400

    formatted_phone = f"+91{phone_10}"
    user_uid = uid or f"kr_{phone_10}"

    # 1. Lookup or create local SQLite User
    user = User.query.filter_by(role=role, phone=phone_10).first()
    if not user:
        user = User.query.filter_by(role=role, phone=formatted_phone).first()

    if not user:
        display_name = full_name or f"{role.title()} {phone_10[-4:]}"
        user = User(
            role=role,
            full_name=display_name,
            phone=phone_10,
            password_hash=generate_password_hash(f"otp_{phone_10}_{user_uid}"),
        )
        user.set_extra({
            "uid": user_uid,
            "auth_provider": "fast2sms_otp",
            "full_phone": formatted_phone,
            "verified_at": datetime.utcnow().isoformat()
        })
        db.session.add(user)
        db.session.commit()
    else:
        extra = user.get_extra()
        extra["uid"] = user_uid
        extra["auth_provider"] = "fast2sms_otp"
        extra["full_phone"] = formatted_phone
        extra["last_otp_login"] = datetime.utcnow().isoformat()
        user.set_extra(extra)
        if full_name and (user.full_name.startswith("Farmer") or user.full_name.startswith("Driver") or user.full_name.startswith("Cluster")):
            user.full_name = full_name
        db.session.commit()

    # 2. Establish user session across the platform
    session["user_id"] = user.id
    session["role"] = user.role
    session["name"] = user.full_name
    session["phone"] = user.phone
    session["auth_provider"] = "fast2sms_otp"
    session.permanent = True

    # 3. Supabase Sync: Upsert user record into 'users' and 'profiles'
    supabase_record = {
        "phone": formatted_phone,
        "raw_phone": phone_10,
        "role": role,
        "full_name": user.full_name,
        "auth_provider": "fast2sms_otp",
        "updated_at": datetime.utcnow().isoformat()
    }

    supabase_sync_status = "skipped_not_configured"
    if supabase.is_configured():
        try:
            # Sync to 'users' table
            supabase.upsert("users", supabase_record, on_conflict="phone")
            # Sync to 'profiles' table
            profile_data = {
                "id": user_uid,
                "phone": formatted_phone,
                "role": role,
                "full_name": user.full_name,
                "auth_provider": "fast2sms_otp",
                "updated_at": datetime.utcnow().isoformat()
            }
            supabase.upsert("profiles", profile_data, on_conflict="phone")
            supabase_sync_status = "synced"
        except Exception as e:
            supabase_sync_status = f"error: {str(e)}"

    # 4. Determine redirect URL
    redirect_map = {
        "farmer": url_for("farmer.dashboard"),
        "driver": url_for("driver.dashboard"),
        "cluster": url_for("cluster.dashboard"),
        "customer": url_for("customer.dashboard"),
        "wholesaler": url_for("wholesaler.dashboard"),
    }
    target_url = redirect_map.get(role, url_for("main.home"))

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.full_name}! Login successful.",
        "user": {
            "id": user.id,
            "role": user.role,
            "name": user.full_name,
            "phone": formatted_phone
        },
        "supabase_sync": supabase_sync_status,
        "redirect_url": target_url
    })



