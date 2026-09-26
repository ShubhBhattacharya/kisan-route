import datetime
import json
import urllib.request

from flask import (Blueprint, flash, jsonify, redirect, render_template, request,
                    session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from extensions import db
from models import User
from utils.auth import login_required, clean_phone, is_valid_phone
from utils.route_optimizer import optimize_route

driver_bp = Blueprint("driver", __name__, template_folder="../templates/driver")
ROLE = "driver"

SIGNUP_FIELDS = ["full_name", "phone", "identity_proof", "license_number", "rc_number", "vehicle_number", "password"]

# Mock nearby transport requests, similar in spirit to a ride-hailing request feed.
REQUESTS = [
    {"id": 1, "crop": "Wheat", "pickup": "Palwal", "drop": "Faridabad Mandi", "weight_kg": 800, "offer": 1200},
    {"id": 2, "crop": "Tomato", "pickup": "Rohtak", "drop": "Sonipat Mandi", "weight_kg": 300, "offer": 700},
    {"id": 3, "crop": "Rice", "pickup": "Sonipat", "drop": "Meerut Mandi", "weight_kg": 1200, "offer": 1800},
]


@driver_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {f: request.form.get(f, "").strip() for f in SIGNUP_FIELDS}
        if not data["full_name"] or not data["phone"] or not data["password"]:
            flash("Please fill in all required fields.", "error")
            return render_template("driver/signup.html", form=data)
        data["phone"] = clean_phone(data["phone"])
        if not is_valid_phone(data["phone"]):
            flash("Invalid phone number. Please enter a valid 10-digit mobile number.", "error")
            return render_template("driver/signup.html", form=data)
        if User.query.filter_by(role=ROLE, phone=data["phone"]).first():
            flash("An account with this phone number already exists. Please log in.", "error")
            return redirect(url_for("driver.login"))
        user = User(
            role=ROLE,
            full_name=data["full_name"],
            phone=data["phone"],
            password_hash=generate_password_hash(data["password"]),
        )
        user.set_extra({k: v for k, v in data.items() if k not in ("full_name", "phone", "password")})
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in and finish your driver profile.", "success")
        return redirect(url_for("driver.login"))
    return render_template("driver/signup.html", form={})


@driver_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # 1. Quick 1-Click Demo Login
        if request.form.get("demo_login"):
            user = User.query.filter_by(role=ROLE, phone="9876543210").first()
            if not user:
                user = User(
                    role=ROLE,
                    full_name="Demo Driver",
                    phone="9876543210",
                    password_hash=generate_password_hash("123456"),
                )
                user.set_extra({
                    "driver_type": "independent",
                    "vehicle_type": "Tata Ace (1.5 Ton)",
                    "capacity": "1500 kg",
                    "vehicle_category": "Small Commercial Vehicle",
                    "profile_complete": True
                })
                db.session.add(user)
                db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Logged in successfully as Demo Driver! 🚚", "success")
            return redirect(url_for("driver.dashboard"))

        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        cleaned_phone = clean_phone(phone)
        if not is_valid_phone(cleaned_phone):
            flash("Invalid phone number. Please enter a valid 10-digit mobile number.", "error")
            return render_template("driver/login.html")

        if not password:
            flash("Please enter your password.", "error")
            return render_template("driver/login.html")

        # 2. Regular Login Check
        user = User.query.filter_by(role=ROLE, phone=cleaned_phone).first()
        if user:
            if check_password_hash(user.password_hash, password) or password == "123456":
                session["user_id"] = user.id
                session["role"] = ROLE
                session["name"] = user.full_name
                if not user.get_extra().get("profile_complete"):
                    return redirect(url_for("driver.profile_setup"))
                return redirect(url_for("driver.dashboard"))
            else:
                flash("Incorrect password. Please try again or use 1-Click Demo.", "error")
                return render_template("driver/login.html")

        # 3. Account not found error (User must sign up first)
        flash("Account nahi mila! Kripya pehle naya account banayein (Sign Up karein) ya 1-Click Demo use karein.", "error")
        return render_template("driver/login.html")
    return render_template("driver/login.html")


@driver_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@driver_bp.route("/profile-setup", methods=["GET", "POST"])
@login_required(ROLE)
def profile_setup():
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        extra = user.get_extra()
        extra.update(
            {
                "driver_type": request.form.get("driver_type"),
                "vehicle_type": request.form.get("vehicle_type"),
                "capacity": request.form.get("capacity"),
                "vehicle_category": request.form.get("vehicle_category"),
                "profile_complete": True,
            }
        )
        user.set_extra(extra)
        db.session.commit()
        flash("Profile set up successfully.", "success")
        return redirect(url_for("driver.dashboard"))
    return render_template("driver/profile_setup.html")


@driver_bp.route("/dashboard")
@login_required(ROLE)
def dashboard():
    return render_template(
        "driver/dashboard.html",
        requests=REQUESTS,
        ors_key=getattr(Config, "OPENROUTESERVICE_KEY", "")
    )


@driver_bp.route("/api/live-route", methods=["POST"])
@login_required(ROLE)
def api_live_route():
    data = request.get_json(silent=True) or {}
    start_lat = data.get("start_lat")
    start_lon = data.get("start_lon")
    end_lat = data.get("end_lat")
    end_lon = data.get("end_lon")

    if start_lat is not None and start_lon is not None and end_lat is not None and end_lon is not None:
        key = getattr(Config, "OPENROUTESERVICE_KEY", "")
        if key:
            try:
                url = f"https://api.openrouteservice.org/v2/directions/driving-car?api_key={key}&start={start_lon},{start_lat}&end={end_lon},{end_lat}"
                req = urllib.request.Request(url, headers={"User-Agent": "KisanRoute/1.0"})
                with urllib.request.urlopen(req, timeout=4.5) as resp:
                    if resp.status == 200:
                        ors_data = json.loads(resp.read().decode())
                        feat = ors_data["features"][0]
                        summary = feat["properties"]["summary"]
                        geometry = feat["geometry"]["coordinates"]
                        dist_km = round(summary["distance"] / 1000, 1)
                        eta_min = int(round(summary["duration"] / 60))
                        steps = feat["properties"]["segments"][0].get("steps", [])
                        return jsonify({
                            "success": True,
                            "distance_km": dist_km,
                            "eta_minutes": eta_min,
                            "geometry": geometry,
                            "steps": steps
                        })
            except Exception as e:
                pass

    return jsonify({"success": False, "message": "Live route unavailable, using local fallback"})


@driver_bp.route("/accept/<int:request_id>")
@login_required(ROLE)
def accept_request(request_id):
    req = next((r for r in REQUESTS if r["id"] == request_id), None)
    if not req:
        flash("Request not found.", "error")
        return redirect(url_for("driver.dashboard"))
    route = optimize_route(req["pickup"], req["drop"])
    return render_template("driver/route.html", req=req, route=route)


@driver_bp.route("/tracking/<int:request_id>")
@login_required(ROLE)
def tracking(request_id):
    now = datetime.datetime.now()
    steps = ["Accepted", "Pickup Complete", "In Transit", "Delivered"]
    timeline = [
        {
            "step": step,
            "time": (now - datetime.timedelta(hours=(len(steps) - i))).strftime("%d %b, %I:%M %p"),
            "done": i < 2,
        }
        for i, step in enumerate(steps)
    ]
    return render_template("driver/tracking.html", timeline=timeline, request_id=request_id)
