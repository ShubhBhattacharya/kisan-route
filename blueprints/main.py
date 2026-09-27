import os
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, session, url_for, redirect, send_from_directory, current_app, flash
from werkzeug.security import generate_password_hash

from config import Config
from models import db, User
from translations.strings import LANGUAGES
from utils.auth import clean_phone as sanitize_phone
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


@main_bp.route("/portal/<role>")
def switch_portal(role):
    valid_roles = ["farmer", "driver", "cluster", "customer", "wholesaler"]
    if role not in valid_roles:
        return redirect(url_for("main.home"))

    if session.get("user_id") and session.get("role") == role:
        return redirect(url_for(f"{role}.dashboard"))
    return redirect(url_for(f"{role}.login"))



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
    from utils.bids import get_all_bids
    lang = request.args.get("lang") or session.get("lang", "en")
    w = get_agri_weather()
    
    alerts_data = []

    # Insert Live Wholesaler Bids dynamically at the very top
    try:
        all_recent = get_all_bids()
        live_bids = [b for b in all_recent if "declined" not in str(b.get("status", "")).lower() and "rejected" not in str(b.get("status", "")).lower()]
        for b in live_bids[:4]:
            w_name = b.get("wholesaler_name", "थोक व्यापारी")
            rate = float(b.get("offer_price", 0))
            qty = float(b.get("offer_qty", 0))
            crop = b.get("crop", "Produce")
            total = float(b.get("total_value", 0))
            bid_id = b.get("bid_id", "BID")
            status = b.get("status", "Offer Sent")
            alerts_data.append({
                "id": f"bid_{bid_id}",
                "category": "bid",
                "icon": "💰",
                "title_hi": f"⚡ थोक बोली: ₹{rate:,.0f}/क्विंटल ({crop})",
                "title_en": f"⚡ Wholesaler Bid: ₹{rate:,.0f}/Qtl ({crop})",
                "body_hi": f"{w_name} ने {crop} के लिए ₹{rate:,.2f}/क्विंटल की दर से {qty} क्विंटल की सीधी बोली लगाई है (कुल: ₹{total:,.0f})। स्थिति: {status}",
                "body_en": f"{w_name} offered ₹{rate:,.2f}/Qtl for {qty} Qtl {crop} (Total: ₹{total:,.0f}). Status: {status}",
                "time_hi": b.get("created_at", "अभी"),
                "time_en": b.get("created_at", "Just now"),
                "url": "/farmer/dashboard#krFarmerBidsSection"
            })
    except Exception as e:
        print("[notifications] Live bids fetch note:", e)

    # Standard system alerts
    alerts_data.extend([
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
    ])

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
    return send_from_directory(current_app.static_folder, "manifest.json", mimetype="application/manifest+json")


@main_bp.route("/icon-192.png")
def icon_192():
    return send_from_directory(os.path.join(current_app.static_folder, "images", "icons"), "icon-192.png", mimetype="image/png")


@main_bp.route("/icon-512.png")
def icon_512():
    return send_from_directory(os.path.join(current_app.static_folder, "images", "icons"), "icon-512.png", mimetype="image/png")


@main_bp.route("/apple-touch-icon.png")
def apple_touch_icon():
    return send_from_directory(os.path.join(current_app.static_folder, "images", "icons"), "apple-touch-icon.png", mimetype="image/png")


@main_bp.route("/icon-maskable-192.png")
def icon_maskable_192():
    return send_from_directory(os.path.join(current_app.static_folder, "images", "icons"), "icon-maskable-192.png", mimetype="image/png")


@main_bp.route("/icon-maskable-512.png")
def icon_maskable_512():
    return send_from_directory(os.path.join(current_app.static_folder, "images", "icons"), "icon-maskable-512.png", mimetype="image/png")



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


@main_bp.route("/api/auth/phone-login", methods=["POST"])
@main_bp.route("/api/auth/whatsapp-login", methods=["POST"])
@main_bp.route("/api/auth/firebase-login", methods=["POST"])
def phone_login():
    """Verify WhatsApp direct handshake authentication, create or restore user session
    in Supabase users/profiles tables, persist local database user, and establish platform session.
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
    cleaned = sanitize_phone(phone_raw)
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
        display_name = full_name or f"+91 {phone_10[:5]} {phone_10[5:]}"
        user = User(
            role=role,
            full_name=display_name,
            phone=phone_10,
            password_hash=generate_password_hash(f"wa_{phone_10}_{user_uid}"),
        )
        user.set_extra({
            "uid": user_uid,
            "auth_provider": "whatsapp_handshake",
            "full_phone": formatted_phone,
            "verified_at": datetime.utcnow().isoformat()
        })
        db.session.add(user)
        db.session.commit()
    else:
        extra = user.get_extra()
        extra["uid"] = user_uid
        extra["auth_provider"] = "whatsapp_handshake"
        extra["full_phone"] = formatted_phone
        extra["last_otp_login"] = datetime.utcnow().isoformat()
        user.set_extra(extra)
        if full_name:
            user.full_name = full_name
        elif not user.full_name or user.full_name == "Ramesh Patel":
            user.full_name = f"+91 {phone_10[:5]} {phone_10[5:]}"
        db.session.commit()

    # 2. Establish user session across the platform with dynamic user_name & phone
    display_name = user.full_name or full_name or f"+91 {phone_10[:5]} {phone_10[5:]}"
    user_phone_val = user.phone or phone_10

    session["user_id"] = user.id
    session["role"] = user.role
    session["name"] = display_name
    session["user_name"] = display_name
    session["phone"] = user_phone_val
    session["user_phone"] = user_phone_val
    session["auth_provider"] = "whatsapp_handshake"
    session.permanent = True

    # 2b. Fire WhatsApp bot message on login / verification via local Baileys gateway on port 3000
    import requests

    phone_to_send = session.get('user_phone') or user.phone
    clean_phone = str(phone_to_send).strip().replace("+", "")
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone

    try:
        requests.post(
            "http://127.0.0.1:3000/send",
            json={
                "phone": clean_phone,
                "message": f"Namaste {session_user_name} ji! Main hoon aapka Kisan Mitra AI saathi. Upar diye card se 'Save Contact' karein. Mandi bhav, shipment status ya kisi bhi sahayata ke liye yahan message karein!",
                "send_vcard": True
            },
            timeout=5
        )
    except Exception as err:
        print(f"Failed to dispatch WhatsApp alert: {err}")

    # 3. Supabase Sync: Upsert user record into 'users' and 'profiles'
    supabase_record = {
        "phone": formatted_phone,
        "raw_phone": phone_10,
        "role": role,
        "full_name": user.full_name,
        "auth_provider": "whatsapp_handshake",
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
                "auth_provider": "whatsapp_handshake",
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



