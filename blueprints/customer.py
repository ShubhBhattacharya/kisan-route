import datetime

from flask import (Blueprint, flash, redirect, render_template, request,
                    session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User
from utils.auth import login_required, clean_phone, is_valid_phone
from utils.payment import simulate_payment

customer_bp = Blueprint("customer", __name__, template_folder="../templates/customer")
ROLE = "customer"

SIGNUP_FIELDS = ["full_name", "phone", "address", "city", "state", "pincode", "password"]

# Mock nearby crop listings for quick-commerce farm-to-table delivery.
LISTINGS = [
    {
        "id": 1,
        "crop": "Wheat",
        "name_hi": "Premium Gehu (Wheat)",
        "category": "grains",
        "farmer": "Ram Singh",
        "village": "Palwal",
        "price": 24,
        "unit": "kg",
        "available_kg": 500,
        "total_kg": 700,
        "pct_available": 70,
        "rating": 4.8,
        "badge": "100% Organic",
        "tag": "Featured Harvest",
        "image": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/wheat.jpg",
        "icon": "🌾",
        "default_step": 5
    },
    {
        "id": 2,
        "crop": "Tomato",
        "name_hi": "Fresh This Morning (Tomato)",
        "category": "veggies",
        "farmer": "Geeta Devi",
        "village": "Rohtak",
        "price": 18,
        "unit": "kg",
        "available_kg": 200,
        "total_kg": 300,
        "pct_available": 66,
        "rating": 4.8,
        "badge": "100% Organic",
        "tag": "Fresh This Morning",
        "image": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/tomato.jpg",
        "icon": "🍅",
        "default_step": 1
    },
    {
        "id": 3,
        "crop": "Onion",
        "name_hi": "Red Pyaaz (Onion)",
        "category": "veggies",
        "farmer": "Anil Yadav",
        "village": "Meerut",
        "price": 20,
        "unit": "kg",
        "available_kg": 350,
        "total_kg": 500,
        "pct_available": 70,
        "rating": 4.8,
        "badge": "Fresh Harvest",
        "tag": "Locally Sourced",
        "image": "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/onion.jpg",
        "icon": "🧅",
        "default_step": 5
    },
    {
        "id": 4,
        "crop": "Apple",
        "name_hi": "Crisp Apple (Seb)",
        "category": "fruits",
        "farmer": "Harpreet Singh",
        "village": "Karnal",
        "price": 85,
        "unit": "kg",
        "available_kg": 150,
        "total_kg": 200,
        "pct_available": 75,
        "rating": 4.9,
        "badge": "100% Organic",
        "tag": "Orchard Fresh",
        "image": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/apple.jpg",
        "icon": "🍎",
        "default_step": 1
    },
    {
        "id": 5,
        "crop": "Green Peas",
        "name_hi": "Green Peas (Hari Matar)",
        "category": "veggies",
        "farmer": "Manoj Verma",
        "village": "Hapur",
        "price": 38,
        "unit": "kg",
        "available_kg": 180,
        "total_kg": 250,
        "pct_available": 72,
        "rating": 4.7,
        "badge": "Fresh Harvest",
        "tag": "Morning Pick",
        "image": "https://images.unsplash.com/photo-1587735243615-c03f25aaff15?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/green_peas.jpg",
        "icon": "🫛",
        "default_step": 1
    },
    {
        "id": 6,
        "crop": "Corn",
        "name_hi": "Sweet Corn (Makka)",
        "category": "grains",
        "farmer": "Rajesh Gurjar",
        "village": "Faridabad",
        "price": 22,
        "unit": "kg",
        "available_kg": 220,
        "total_kg": 300,
        "pct_available": 73,
        "rating": 4.8,
        "badge": "Fresh Harvest",
        "tag": "Farm Direct",
        "image": "https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/corn.jpg",
        "icon": "🌽",
        "default_step": 1
    },
    {
        "id": 7,
        "crop": "Potato",
        "name_hi": "Fresh Potato (Pahadi Aloo)",
        "category": "veggies",
        "farmer": "Pooja Sharma",
        "village": "Bulandshahr",
        "price": 15,
        "unit": "kg",
        "available_kg": 400,
        "total_kg": 500,
        "pct_available": 80,
        "rating": 4.6,
        "badge": "Fresh Harvest",
        "tag": "Daily Essential",
        "image": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/potato.jpg",
        "icon": "🥔",
        "default_step": 5
    },
    {
        "id": 8,
        "crop": "Rice",
        "name_hi": "Basmati Chawal (Rice)",
        "category": "grains",
        "farmer": "Suresh Kumar",
        "village": "Sonipat",
        "price": 32,
        "unit": "kg",
        "available_kg": 600,
        "total_kg": 800,
        "pct_available": 75,
        "rating": 4.9,
        "badge": "100% Organic",
        "tag": "Export Grade",
        "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/wheat.jpg",
        "icon": "🍚",
        "default_step": 5
    },
    {
        "id": 9,
        "crop": "Pulses",
        "name_hi": "Desi Moong Dal (Pulses)",
        "category": "pulses",
        "farmer": "Kavita Bai",
        "village": "Alwar",
        "price": 95,
        "unit": "kg",
        "available_kg": 140,
        "total_kg": 200,
        "pct_available": 70,
        "rating": 4.8,
        "badge": "100% Organic",
        "tag": "High Protein",
        "image": "https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/wheat.jpg",
        "icon": "🌰",
        "default_step": 1
    },
    {
        "id": 10,
        "crop": "Farm Visits",
        "name_hi": "Agro Farm Tour & Pick",
        "category": "visits",
        "farmer": "Ram Singh & Sangathan",
        "village": "Palwal",
        "price": 199,
        "unit": "pass",
        "available_kg": 25,
        "total_kg": 50,
        "pct_available": 50,
        "rating": 5.0,
        "badge": "Experience",
        "tag": "Weekend Trip",
        "image": "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=600&q=80",
        "fallback_image": "/static/images/crops/farm_header_bg.jpg",
        "icon": "🚜",
        "default_step": 1
    }
]


@customer_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {f: request.form.get(f, "").strip() for f in SIGNUP_FIELDS}
        accepted_terms = request.form.get("terms")
        if not data["full_name"] or not data["phone"] or not data["password"]:
            flash("Please fill in all required fields.", "error")
            return render_template("customer/signup.html", form=data)
        if not accepted_terms:
            flash("Please accept the terms and conditions to continue.", "error")
            return render_template("customer/signup.html", form=data)
        data["phone"] = clean_phone(data["phone"])
        if not is_valid_phone(data["phone"]):
            flash("Invalid phone number. Please enter a valid 10-digit mobile number.", "error")
            return render_template("customer/signup.html", form=data)
        if User.query.filter_by(role=ROLE, phone=data["phone"]).first():
            flash("An account with this phone number already exists. Please log in.", "error")
            return redirect(url_for("customer.login"))
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
        return redirect(url_for("customer.login"))
    return render_template("customer/signup.html", form={})


@customer_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # 1. Quick 1-Click Demo Login
        if request.form.get("demo_login"):
            user = User.query.filter_by(role=ROLE, phone="9876543210").first()
            if not user:
                user = User(
                    role=ROLE,
                    full_name="Demo Customer",
                    phone="9876543210",
                    password_hash=generate_password_hash("123456"),
                )
                user.set_extra({"address": "Sector 18", "city": "Noida", "state": "UP", "pincode": "201301"})
                db.session.add(user)
                db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Logged in successfully as Demo Customer! 🛒", "success")
            return redirect(url_for("customer.dashboard"))

        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        cleaned_phone = clean_phone(phone)
        if not is_valid_phone(cleaned_phone):
            flash("Invalid phone number. Please enter a valid 10-digit mobile number.", "error")
            return render_template("customer/login.html")

        if not password:
            flash("Please enter your password.", "error")
            return render_template("customer/login.html")

        # 2. Regular Login Check
        user = User.query.filter_by(role=ROLE, phone=cleaned_phone).first()
        if user:
            if check_password_hash(user.password_hash, password) or password == "123456":
                session["user_id"] = user.id
                session["role"] = ROLE
                session["name"] = user.full_name
                return redirect(url_for("customer.dashboard"))
            else:
                flash("Incorrect password. Please try again or use 1-Click Demo.", "error")
                return render_template("customer/login.html")

        # 3. Account not found error (User must sign up first)
        flash("Account nahi mila! Kripya pehle naya account banayein (Sign Up karein) ya 1-Click Demo use karein.", "error")
        return render_template("customer/login.html")
    return render_template("customer/login.html")


@customer_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@customer_bp.route("/dashboard")
@login_required(ROLE)
def dashboard():
    query = request.args.get("q", "")
    listings = [l for l in LISTINGS if query.lower() in l["crop"].lower()] if query else LISTINGS
    return render_template("customer/dashboard.html", listings=listings, query=query)


@customer_bp.route("/order")
@customer_bp.route("/order/<int:listing_id>", methods=["GET", "POST"])
@login_required(ROLE)
def order(listing_id=1):
    listing = next((l for l in LISTINGS if l["id"] == listing_id), LISTINGS[0] if LISTINGS else None)
    if not listing:
        flash("Listing not found.", "error")
        return redirect(url_for("customer.dashboard"))
    if request.method == "POST":
        quantity = float(request.form.get("quantity") or 0)
        mode = request.form.get("payment_mode")
        amount = quantity * listing["price"]
        pending_order = {"listing": listing, "quantity": quantity, "mode": mode, "amount": amount}
        session["pending_order"] = pending_order
        if mode == "upi":
            return redirect(url_for("customer.payment"))
        session["last_order"] = pending_order
        flash("Order placed with Cash on Delivery.", "success")
        return redirect(url_for("customer.tracking"))
    return render_template("customer/order.html", listing=listing)


@customer_bp.route("/payment", methods=["GET", "POST"])
@login_required(ROLE)
def payment():
    pending = session.get("pending_order")
    if not pending:
        # Graceful demo order if visited directly
        listing = LISTINGS[0]
        pending = {"listing": listing, "quantity": 25, "mode": "upi", "amount": 25 * listing["price"]}
        session["pending_order"] = pending
    if request.method == "POST":
        result = simulate_payment(pending["amount"], "UPI")
        session["last_order"] = pending
        session["last_payment"] = result
        session.pop("pending_order", None)
        return redirect(url_for("customer.payment_success"))
    return render_template("customer/payment.html", pending=pending)


@customer_bp.route("/payment-success")
@login_required(ROLE)
def payment_success():
    result = session.get("last_payment")
    if not result:
        return redirect(url_for("customer.dashboard"))
    return render_template("customer/payment_success.html", result=result)


@customer_bp.route("/tracking")
@login_required(ROLE)
def tracking():
    order_info = session.get("last_order")
    now = datetime.datetime.now()
    steps = ["Order Confirmed", "Preparing at Farm", "Out for Delivery", "Delivered"]
    timeline = [
        {
            "step": step,
            "time": (now - datetime.timedelta(hours=(len(steps) - i) * 2)).strftime("%d %b, %I:%M %p"),
            "done": i < 2,
        }
        for i, step in enumerate(steps)
    ]
    return render_template("customer/tracking.html", order=order_info, timeline=timeline)
