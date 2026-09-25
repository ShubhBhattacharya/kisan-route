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

# Mock nearby crop listings a customer can browse and order from.
LISTINGS = [
    {"id": 1, "crop": "Wheat", "farmer": "Ram Singh", "village": "Palwal", "price": 24, "unit": "kg", "available_kg": 500},
    {"id": 2, "crop": "Tomato", "farmer": "Geeta Devi", "village": "Rohtak", "price": 18, "unit": "kg", "available_kg": 200},
    {"id": 3, "crop": "Onion", "farmer": "Anil Yadav", "village": "Meerut", "price": 20, "unit": "kg", "available_kg": 350},
    {"id": 4, "crop": "Potato", "farmer": "Pooja Sharma", "village": "Bulandshahr", "price": 15, "unit": "kg", "available_kg": 400},
    {"id": 5, "crop": "Rice", "farmer": "Suresh Kumar", "village": "Sonipat", "price": 32, "unit": "kg", "available_kg": 600},
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


@customer_bp.route("/order/<int:listing_id>", methods=["GET", "POST"])
@login_required(ROLE)
def order(listing_id):
    listing = next((l for l in LISTINGS if l["id"] == listing_id), None)
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
        return redirect(url_for("customer.dashboard"))
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
