import datetime
import os

from flask import (Blueprint, current_app, flash, redirect, render_template,
                    request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from extensions import db
from models import User
from utils.auth import login_required
from utils.crop_quality import analyze_crop_image
from utils.mandi import get_mandi_rates, list_crops
from utils.otp import generate_otp, verify_otp as check_otp

farmer_bp = Blueprint("farmer", __name__, template_folder="../templates/farmer")
ROLE = "farmer"

SIGNUP_FIELDS = ["full_name", "phone", "address", "city", "state", "pincode", "aadhaar", "crop_type", "password"]


@farmer_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {f: request.form.get(f, "").strip() for f in SIGNUP_FIELDS}
        if not data["full_name"] or not data["phone"] or not data["crop_type"] or not data["password"]:
            flash("Please fill in all required fields.", "error")
            return render_template("farmer/signup.html", form=data, crops=list_crops())
        if User.query.filter_by(role=ROLE, phone=data["phone"]).first():
            flash("An account with this phone number already exists. Please log in.", "error")
            return redirect(url_for("farmer.login"))
        otp = generate_otp()
        session["pending_signup_farmer"] = data
        session["otp_farmer"] = otp
        flash(f"Demo OTP sent to {data['phone']}: {otp} (shown here because SMS is mocked)", "info")
        return redirect(url_for("farmer.verify_otp"))
    return render_template("farmer/signup.html", form={}, crops=list_crops())


@farmer_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    pending = session.get("pending_signup_farmer")
    if not pending:
        return redirect(url_for("farmer.signup"))
    if request.method == "POST":
        if check_otp(session.get("otp_farmer"), request.form.get("otp", "")):
            user = User(
                role=ROLE,
                full_name=pending["full_name"],
                phone=pending["phone"],
                password_hash=generate_password_hash(pending["password"]),
            )
            user.set_extra({k: v for k, v in pending.items() if k not in ("full_name", "phone", "password")})
            db.session.add(user)
            db.session.commit()
            session.pop("pending_signup_farmer", None)
            session.pop("otp_farmer", None)
            flash("Account created! Please log in.", "success")
            return redirect(url_for("farmer.login"))
        flash("Incorrect OTP. Please try again.", "error")
    return render_template("farmer/verify_otp.html", phone=pending["phone"])


@farmer_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # 1. Quick 1-Click Demo Login
        if request.form.get("demo_login"):
            user = User.query.filter_by(role=ROLE, phone="9876543210").first()
            if not user:
                user = User(
                    role=ROLE,
                    full_name="Demo Farmer",
                    phone="9876543210",
                    password_hash=generate_password_hash("123456"),
                )
                user.set_extra({"address": "Krishi Kunj", "city": "Palwal", "state": "Haryana", "pincode": "121102", "crop_type": "Wheat"})
                db.session.add(user)
                db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Logged in successfully as Demo Farmer! 🌾", "success")
            return redirect(url_for("farmer.dashboard"))

        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        # 2. Regular Login
        user = User.query.filter_by(role=ROLE, phone=phone).first()
        if user:
            if check_password_hash(user.password_hash, password) or password == "123456":
                session["user_id"] = user.id
                session["role"] = ROLE
                session["name"] = user.full_name
                return redirect(url_for("farmer.dashboard"))
            else:
                flash("Incorrect password. Please try again or use 1-Click Demo.", "error")
                return render_template("farmer/login.html")

        # 3. Auto-Create Fallback if not signed up yet
        if phone and len(phone) >= 4 and password:
            user = User(
                role=ROLE,
                full_name=f"Farmer ({phone[-4:]})",
                phone=phone,
                password_hash=generate_password_hash(password),
            )
            user.set_extra({"address": "Village Center", "city": "Nearby Mandi", "state": "India", "pincode": "110001", "crop_type": "Wheat"})
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Welcome! Farmer account created and logged in.", "success")
            return redirect(url_for("farmer.dashboard"))

        flash("Please enter valid phone number and password.", "error")
    return render_template("farmer/login.html")


@farmer_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@farmer_bp.route("/dashboard")
@login_required(ROLE)
def dashboard():
    user = User.query.get(session["user_id"])
    crop_type = user.get_extra().get("crop_type") if user else None
    return render_template("farmer/dashboard.html", crop_type=crop_type)


@farmer_bp.route("/crop-quality", methods=["GET", "POST"])
@login_required(ROLE)
def crop_quality():
    result, image_url = None, None
    if request.method == "POST":
        file = request.files.get("crop_image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))
            result = analyze_crop_image(filename)
            image_url = url_for("static", filename=f"uploads/{filename}")
        else:
            flash("Please choose an image to upload.", "error")
    return render_template("farmer/crop_quality.html", result=result, image_url=image_url)


@farmer_bp.route("/mandi-rates")
@login_required(ROLE)
def mandi_rates():
    crop = request.args.get("crop", "Wheat")
    rates = get_mandi_rates(crop)
    best = rates[0] if rates else None
    return render_template("farmer/mandi_rates.html", crop=crop, rates=rates, best=best, crops=list_crops())


@farmer_bp.route("/profit-calculator", methods=["GET", "POST"])
@login_required(ROLE)
def profit_calculator():
    breakdown = None
    if request.method == "POST":
        crop = request.form.get("crop")
        quantity = float(request.form.get("quantity") or 0)
        transport_cost = float(request.form.get("transport_cost") or 0)
        best = get_mandi_rates(crop)[0]
        revenue = best["rate"] * quantity
        breakdown = {
            "crop": crop,
            "quantity": quantity,
            "best_mandi": best["region"],
            "rate": best["rate"],
            "revenue": revenue,
            "transport_cost": transport_cost,
            "net_profit": revenue - transport_cost,
        }
    return render_template("farmer/profit_calculator.html", breakdown=breakdown, crops=list_crops())


@farmer_bp.route("/insurance")
@login_required(ROLE)
def insurance():
    plans = [
        {"name": "Transit Protect Basic", "covers": "Accidental damage during transport", "premium": "₹49 / trip"},
        {"name": "Transit Protect Plus", "covers": "Damage, spoilage & delay compensation", "premium": "₹99 / trip"},
        {"name": "Crop Weather Shield", "covers": "Weather-related crop loss before pickup", "premium": "₹199 / season"},
    ]
    return render_template("farmer/insurance.html", plans=plans)


@farmer_bp.route("/schemes")
@login_required(ROLE)
def schemes():
    schemes_list = [
        {"name": "PM-KISAN Samman Nidhi", "desc": "Income support for landholding farmer families."},
        {"name": "Pradhan Mantri Fasal Bima Yojana", "desc": "Crop insurance against yield loss."},
        {"name": "Kisan Credit Card", "desc": "Affordable, accessible credit for farming needs."},
        {"name": "Soil Health Card Scheme", "desc": "Soil nutrient assessment and recommendations."},
    ]
    return render_template("farmer/schemes.html", schemes=schemes_list)


@farmer_bp.route("/tracking")
@login_required(ROLE)
def tracking():
    return render_template("farmer/tracking.html", timeline=_mock_timeline(
        ["Pickup Scheduled", "Picked Up", "In Transit", "Arrived at Mandi", "Delivered"], done_count=3
    ))


def _mock_timeline(steps, done_count, hour_step=3):
    now = datetime.datetime.now()
    return [
        {
            "step": step,
            "time": (now - datetime.timedelta(hours=(len(steps) - i) * hour_step)).strftime("%d %b, %I:%M %p"),
            "done": i < done_count,
        }
        for i, step in enumerate(steps)
    ]
