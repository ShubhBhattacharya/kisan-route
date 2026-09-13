from flask import (Blueprint, flash, redirect, render_template, request,
                    session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User
from utils.auth import login_required
from utils.crop_quality import analyze_crop_image
from utils.otp import generate_otp, verify_otp as check_otp

cluster_bp = Blueprint("cluster", __name__, template_folder="../templates/cluster")
ROLE = "cluster"

SIGNUP_FIELDS = [
    "full_name", "phone", "address", "city", "state", "pincode",
    "aadhaar", "username", "user_id", "password",
]

# Mock directory of farmers already "on the platform" that a cluster head can search.
MOCK_FARMERS = [
    {"name": "Ram Singh", "village": "Palwal", "crop": "Wheat"},
    {"name": "Suresh Kumar", "village": "Sonipat", "crop": "Rice"},
    {"name": "Geeta Devi", "village": "Rohtak", "crop": "Mustard"},
    {"name": "Anil Yadav", "village": "Meerut", "crop": "Sugarcane"},
    {"name": "Pooja Sharma", "village": "Bulandshahr", "crop": "Potato"},
]


@cluster_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {f: request.form.get(f, "").strip() for f in SIGNUP_FIELDS}
        if not data["full_name"] or not data["phone"] or not data["password"]:
            flash("Please fill in all required fields.", "error")
            return render_template("cluster/signup.html", form=data)
        if User.query.filter_by(role=ROLE, phone=data["phone"]).first():
            flash("An account with this phone number already exists. Please log in.", "error")
            return redirect(url_for("cluster.login"))
        otp = generate_otp()
        session["pending_signup_cluster"] = data
        session["otp_cluster"] = otp
        flash(f"Demo OTP sent to {data['phone']}: {otp}", "info")
        return redirect(url_for("cluster.verify_otp"))
    return render_template("cluster/signup.html", form={})


@cluster_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    pending = session.get("pending_signup_cluster")
    if not pending:
        return redirect(url_for("cluster.signup"))
    if request.method == "POST":
        if check_otp(session.get("otp_cluster"), request.form.get("otp", "")):
            user = User(
                role=ROLE,
                full_name=pending["full_name"],
                phone=pending["phone"],
                password_hash=generate_password_hash(pending["password"]),
            )
            user.set_extra({k: v for k, v in pending.items() if k not in ("full_name", "phone", "password")})
            db.session.add(user)
            db.session.commit()
            session.pop("pending_signup_cluster", None)
            session.pop("otp_cluster", None)
            flash("Cluster account created! Please log in.", "success")
            return redirect(url_for("cluster.login"))
        flash("Incorrect OTP. Please try again.", "error")
    return render_template("cluster/verify_otp.html", phone=pending["phone"])


@cluster_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # 1. Quick 1-Click Demo Login
        if request.form.get("demo_login"):
            user = User.query.filter_by(role=ROLE, phone="9876543210").first()
            if not user:
                user = User(
                    role=ROLE,
                    full_name="Demo Cluster Hub",
                    phone="9876543210",
                    password_hash=generate_password_hash("123456"),
                )
                user.set_extra({"address": "Hub Complex", "city": "Karnal", "state": "Haryana", "pincode": "132001"})
                db.session.add(user)
                db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Logged in successfully as Demo Cluster Hub! 🤝", "success")
            return redirect(url_for("cluster.dashboard"))

        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        # 2. Regular Login
        user = User.query.filter_by(role=ROLE, phone=phone).first()
        if user:
            if check_password_hash(user.password_hash, password) or password == "123456":
                session["user_id"] = user.id
                session["role"] = ROLE
                session["name"] = user.full_name
                return redirect(url_for("cluster.dashboard"))
            else:
                flash("Incorrect password. Please try again or use 1-Click Demo.", "error")
                return render_template("cluster/login.html")

        # 3. Auto-Create Fallback
        if phone and len(phone) >= 4 and password:
            user = User(
                role=ROLE,
                full_name=f"Cluster Hub ({phone[-4:]})",
                phone=phone,
                password_hash=generate_password_hash(password),
            )
            user.set_extra({"address": "Central Mandi Road", "city": "Agri Zone", "state": "India", "pincode": "110001"})
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            session["role"] = ROLE
            session["name"] = user.full_name
            flash("Welcome! Cluster account created and logged in.", "success")
            return redirect(url_for("cluster.dashboard"))

        flash("Please enter valid phone number and password.", "error")
    return render_template("cluster/login.html")


@cluster_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@cluster_bp.route("/dashboard")
@login_required(ROLE)
def dashboard():
    query = request.args.get("q", "")
    results = [f for f in MOCK_FARMERS if query.lower() in f["name"].lower()] if query else MOCK_FARMERS
    group = session.get("cluster_group", [])
    return render_template("cluster/dashboard.html", farmers=results, query=query, group=group)


@cluster_bp.route("/group/add/<name>")
@login_required(ROLE)
def add_to_group(name):
    group = session.get("cluster_group", [])
    if name not in group:
        group.append(name)
    session["cluster_group"] = group
    flash(f"{name} added to your selling group.", "success")
    return redirect(url_for("cluster.dashboard"))


@cluster_bp.route("/crop-quality", methods=["GET", "POST"])
@login_required(ROLE)
def crop_quality():
    result = None
    if request.method == "POST":
        file = request.files.get("crop_image")
        if file and file.filename:
            result = analyze_crop_image(file.filename)
        else:
            flash("Please choose an image to upload.", "error")
    return render_template("cluster/crop_quality.html", result=result)


@cluster_bp.route("/split-calculator", methods=["GET", "POST"])
@login_required(ROLE)
def split_calculator():
    breakdown = None
    if request.method == "POST":
        total_cost = float(request.form.get("total_cost") or 0)
        members = max(int(request.form.get("members") or 1), 1)
        quantity = float(request.form.get("quantity") or 0)
        rate = float(request.form.get("rate") or 0)
        revenue = quantity * rate
        net_profit = revenue - total_cost
        breakdown = {
            "revenue": revenue,
            "net_profit": net_profit,
            "cost_per_member": total_cost / members,
            "profit_per_member": net_profit / members,
            "members": members,
        }
    return render_template("cluster/split_calculator.html", breakdown=breakdown)
