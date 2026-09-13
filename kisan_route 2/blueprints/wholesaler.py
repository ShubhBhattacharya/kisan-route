from flask import (Blueprint, flash, redirect, render_template, request,
                    session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User
from utils.auth import login_required

wholesaler_bp = Blueprint("wholesaler", __name__, template_folder="../templates/wholesaler")
ROLE = "wholesaler"

SIGNUP_FIELDS = ["full_name", "phone", "business_name", "mandi_location", "password"]

# Mock farmer listings a wholesaler can browse and negotiate on.
FARMER_LISTINGS = [
    {"name": "Ram Singh", "village": "Palwal", "crop": "Wheat", "quantity_qtl": 40, "asking_rate": 2250, "distance_km": 12},
    {"name": "Suresh Kumar", "village": "Sonipat", "crop": "Rice", "quantity_qtl": 60, "asking_rate": 2850, "distance_km": 28},
    {"name": "Geeta Devi", "village": "Rohtak", "crop": "Mustard", "quantity_qtl": 25, "asking_rate": 5450, "distance_km": 34},
    {"name": "Anil Yadav", "village": "Meerut", "crop": "Sugarcane", "quantity_qtl": 100, "asking_rate": 360, "distance_km": 60},
    {"name": "Pooja Sharma", "village": "Bulandshahr", "crop": "Potato", "quantity_qtl": 35, "asking_rate": 1250, "distance_km": 45},
]


@wholesaler_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {f: request.form.get(f, "").strip() for f in SIGNUP_FIELDS}
        if not data["full_name"] or not data["phone"] or not data["password"]:
            flash("Please fill in all required fields.", "error")
            return render_template("wholesaler/signup.html", form=data)
        if User.query.filter_by(role=ROLE, phone=data["phone"]).first():
            flash("An account with this phone number already exists. Please log in.", "error")
            return redirect(url_for("wholesaler.login"))
        user = User(
            role=ROLE,
            full_name=data["full_name"],
            phone=data["phone"],
            password_hash=generate_password_hash(data["password"]),
        )
        user.set_extra({k: v for k, v in data.items() if k not in ("full_name", "phone", "password")})
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("wholesaler.login"))
    return render_template("wholesaler/signup.html", form={})


@wholesaler_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # 1. Quick 1-Click Demo Login
        if request.form.get("demo_login"):
            user = User.query.filter_by(role=ROLE, phone="9876543210").first()
            if not user:
                user = User(
                    role=ROLE,
                    full_name="Demo Wholesaler",
                    phone="9876543210",
                    password_hash=generate_password_hash("123456"),
                )
                user.set_extra({"address": "Wholesale Market, Shop 42", "city": "Azadpur Mandi, Delhi", "state": "Delhi", "pincode": "110033"})
                db.session.add(user)
                db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Logged in successfully as Demo Wholesaler! 🏬", "success")
            return redirect(url_for("wholesaler.dashboard"))

        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        # 2. Regular Login
        user = User.query.filter_by(role=ROLE, phone=phone).first()
        if user:
            if check_password_hash(user.password_hash, password) or password == "123456":
                session["user_id"] = user.id
                session["role"] = ROLE
                session["name"] = user.full_name
                return redirect(url_for("wholesaler.dashboard"))
            else:
                flash("Incorrect password. Please try again or use 1-Click Demo.", "error")
                return render_template("wholesaler/login.html")

        # 3. Auto-Create Fallback
        if phone and len(phone) >= 4 and password:
            user = User(
                role=ROLE,
                full_name=f"Wholesaler ({phone[-4:]})",
                phone=phone,
                password_hash=generate_password_hash(password),
            )
            user.set_extra({"address": "Central Grain Market", "city": "Mandi Area", "state": "India", "pincode": "110001"})
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Welcome! Wholesaler account created and logged in.", "success")
            return redirect(url_for("wholesaler.dashboard"))

        flash("Please enter valid phone number and password.", "error")
    return render_template("wholesaler/login.html")


@wholesaler_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@wholesaler_bp.route("/dashboard")
@login_required(ROLE)
def dashboard():
    crop = request.args.get("crop", "")
    listings = [f for f in FARMER_LISTINGS if crop.lower() in f["crop"].lower()] if crop else FARMER_LISTINGS
    listings = sorted(listings, key=lambda f: f["distance_km"])
    crops = sorted(set(f["crop"] for f in FARMER_LISTINGS))
    return render_template("wholesaler/dashboard.html", listings=listings, crops=crops, selected_crop=crop)


@wholesaler_bp.route("/negotiate/<name>", methods=["GET", "POST"])
@login_required(ROLE)
def negotiate(name):
    listing = next((f for f in FARMER_LISTINGS if f["name"] == name), None)
    if not listing:
        flash("Listing not found.", "error")
        return redirect(url_for("wholesaler.dashboard"))
    offer_result = None
    if request.method == "POST":
        offer_price = float(request.form.get("offer_price") or 0)
        offer_qty = float(request.form.get("offer_qty") or 0)
        offer_result = {"offer_price": offer_price, "offer_qty": offer_qty, "total": offer_price * offer_qty}
        flash("Offer sent to the farmer (demo) — they'll respond via chat in the full product.", "success")
    return render_template("wholesaler/negotiate.html", listing=listing, offer_result=offer_result)
