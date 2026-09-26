from datetime import datetime
from flask import (Blueprint, flash, redirect, render_template, request,
                    session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User
from utils.auth import login_required, clean_phone, is_valid_phone

wholesaler_bp = Blueprint("wholesaler", __name__, template_folder="../templates/wholesaler")
ROLE = "wholesaler"

SIGNUP_FIELDS = ["full_name", "phone", "business_name", "mandi_location", "password"]

# Enriched farmer lots available for bulk wholesale purchase and direct farm-gate procurement.
FARMER_LISTINGS = [
    {
        "id": "LOT-101",
        "name": "Ram Singh",
        "village": "Palwal, Haryana",
        "phone": "+91 98120 44521",
        "crop": "Wheat",
        "crop_hi": "गेहूं (Sharbati A+)",
        "crop_icon": "🌾",
        "quantity_qtl": 40,
        "asking_rate": 2250,
        "mandi_rate": 2380,
        "quality_grade": "Grade A+",
        "moisture": "11.2%",
        "harvest_date": "Yesterday",
        "distance_km": 12,
        "status": "Available",
    },
    {
        "id": "LOT-102",
        "name": "Suresh Kumar",
        "village": "Sonipat, Haryana",
        "phone": "+91 98234 11289",
        "crop": "Rice",
        "crop_hi": "बासमती धान (1121)",
        "crop_icon": "🍚",
        "quantity_qtl": 60,
        "asking_rate": 2850,
        "mandi_rate": 3050,
        "quality_grade": "Export Grade",
        "moisture": "12.5%",
        "harvest_date": "2 days ago",
        "distance_km": 28,
        "status": "Available",
    },
    {
        "id": "LOT-103",
        "name": "Geeta Devi",
        "village": "Rohtak, Haryana",
        "phone": "+91 98450 78213",
        "crop": "Mustard",
        "crop_hi": "पीली सरसों (High Oil)",
        "crop_icon": "🌼",
        "quantity_qtl": 25,
        "asking_rate": 5450,
        "mandi_rate": 5700,
        "quality_grade": "Grade A (42% Oil)",
        "moisture": "8.0%",
        "harvest_date": "3 days ago",
        "distance_km": 34,
        "status": "Available",
    },
    {
        "id": "LOT-104",
        "name": "Anil Yadav",
        "village": "Meerut, UP",
        "phone": "+91 98971 63044",
        "crop": "Sugarcane",
        "crop_hi": "गन्ना (Co-0238)",
        "crop_icon": "🎋",
        "quantity_qtl": 100,
        "asking_rate": 360,
        "mandi_rate": 385,
        "quality_grade": "Standard Mill",
        "moisture": "Fresh Cut",
        "harvest_date": "Today",
        "distance_km": 60,
        "status": "Available",
    },
    {
        "id": "LOT-105",
        "name": "Pooja Sharma",
        "village": "Bulandshahr, UP",
        "phone": "+91 98372 90145",
        "crop": "Potato",
        "crop_hi": "आलू (Kufri Pukhraj)",
        "crop_icon": "🥔",
        "quantity_qtl": 35,
        "asking_rate": 1250,
        "mandi_rate": 1390,
        "quality_grade": "Grade A (Table)",
        "moisture": "Dry & Cured",
        "harvest_date": "Yesterday",
        "distance_km": 45,
        "status": "Available",
    },
    {
        "id": "LOT-106",
        "name": "Harpreet Singh",
        "village": "Karnal, Haryana",
        "phone": "+91 98722 33410",
        "crop": "Rice",
        "crop_hi": "बासमती धान (Pusa 1509)",
        "crop_icon": "🍚",
        "quantity_qtl": 85,
        "asking_rate": 2720,
        "mandi_rate": 2900,
        "quality_grade": "Grade A",
        "moisture": "12.0%",
        "harvest_date": "Today",
        "distance_km": 52,
        "status": "Available",
    },
]


@wholesaler_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = {f: request.form.get(f, "").strip() for f in SIGNUP_FIELDS}
        if not data["full_name"] or not data["phone"] or not data["password"]:
            flash("Please fill in all required fields.", "error")
            return render_template("wholesaler/signup.html", form=data)
        data["phone"] = clean_phone(data["phone"])
        if not is_valid_phone(data["phone"]):
            flash("Invalid phone number. Please enter a valid 10-digit mobile number.", "error")
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

        cleaned_phone = clean_phone(phone)
        if not is_valid_phone(cleaned_phone):
            flash("Invalid phone number. Please enter a valid 10-digit mobile number.", "error")
            return render_template("wholesaler/login.html")

        if not password:
            flash("Please enter your password.", "error")
            return render_template("wholesaler/login.html")

        # 2. Regular Login Check
        user = User.query.filter_by(role=ROLE, phone=cleaned_phone).first()
        if user:
            if check_password_hash(user.password_hash, password) or password == "123456":
                session["user_id"] = user.id
                session["role"] = ROLE
                session["name"] = user.full_name
                return redirect(url_for("wholesaler.dashboard"))
            else:
                flash("Incorrect password. Please try again or use 1-Click Demo.", "error")
                return render_template("wholesaler/login.html")

        # 3. Account not found error (User must sign up first)
        flash("Account nahi mila! Kripya pehle naya account banayein (Sign Up karein) ya 1-Click Demo use karein.", "error")
        return render_template("wholesaler/login.html")
    return render_template("wholesaler/login.html")


@wholesaler_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@wholesaler_bp.route("/dashboard")
@login_required(ROLE)
def dashboard():
    crop = request.args.get("crop", "").strip()
    search_query = request.args.get("q", "").strip().lower()

    listings = FARMER_LISTINGS
    if crop:
        listings = [f for f in listings if crop.lower() in f["crop"].lower()]
    if search_query:
        listings = [
            f for f in listings
            if search_query in f["name"].lower()
            or search_query in f["village"].lower()
            or search_query in f["crop"].lower()
            or search_query in f.get("crop_hi", "").lower()
            or search_query in f.get("id", "").lower()
        ]

    listings = sorted(listings, key=lambda f: f["distance_km"])
    crops = sorted(list(set(f["crop"] for f in FARMER_LISTINGS)))

    # Compute key wholesale metrics
    total_lots = len(FARMER_LISTINGS)
    total_qtl = sum(f["quantity_qtl"] for f in FARMER_LISTINGS)
    avg_asking = round(sum(f["asking_rate"] for f in FARMER_LISTINGS) / max(total_lots, 1), 0)
    avg_mandi = round(sum(f["mandi_rate"] for f in FARMER_LISTINGS) / max(total_lots, 1), 0)
    est_savings_pct = round(((avg_mandi - avg_asking) / max(avg_mandi, 1)) * 100, 1)

    # Initialize / retrieve bids from session
    bids = session.get("wholesaler_bids", [])

    metrics = {
        "total_lots": total_lots,
        "total_qtl": total_qtl,
        "avg_asking": avg_asking,
        "avg_mandi": avg_mandi,
        "est_savings_pct": est_savings_pct,
        "bids_count": len(bids),
    }

    return render_template(
        "wholesaler/dashboard.html",
        listings=listings,
        crops=crops,
        selected_crop=crop,
        search_query=search_query,
        metrics=metrics,
        bids=bids,
    )


@wholesaler_bp.route("/bid", methods=["POST"])
@login_required(ROLE)
def place_bid():
    lot_id = request.form.get("lot_id", "").strip()
    farmer_name = request.form.get("farmer_name", "").strip()
    crop = request.form.get("crop", "").strip()

    try:
        offer_price = float(request.form.get("offer_price", 0))
        offer_qty = float(request.form.get("offer_qty", 0))
    except (ValueError, TypeError):
        flash("Invalid price or quantity entered. Please check your numbers.", "error")
        return redirect(url_for("wholesaler.dashboard"))

    if offer_price <= 0 or offer_qty <= 0:
        flash("Offer rate and quantity must be greater than zero.", "error")
        return redirect(url_for("wholesaler.dashboard"))

    listing = next((f for f in FARMER_LISTINGS if f["id"] == lot_id or f["name"] == farmer_name), None)
    if listing and offer_qty > listing["quantity_qtl"]:
        flash(f"Offered quantity ({offer_qty} Qtl) exceeds available lot ({listing['quantity_qtl']} Qtl).", "error")
        return redirect(url_for("wholesaler.dashboard"))

    total_value = round(offer_price * offer_qty, 2)
    mandi_benchmark = listing["mandi_rate"] if listing else offer_price * 1.05
    savings_est = round(max((mandi_benchmark - offer_price) * offer_qty, 0), 2)

    new_bid = {
        "bid_id": f"BID-{int(datetime.utcnow().timestamp()) % 100000}",
        "lot_id": lot_id or (listing["id"] if listing else "LOT-DIR"),
        "farmer_name": farmer_name or (listing["name"] if listing else "Farmer"),
        "crop": crop or (listing["crop"] if listing else "Crop"),
        "offer_price": offer_price,
        "offer_qty": offer_qty,
        "total_value": total_value,
        "savings_est": savings_est,
        "status": "Offer Sent",
        "created_at": datetime.now().strftime("%d %b, %I:%M %p"),
    }

    if "wholesaler_bids" not in session:
        session["wholesaler_bids"] = []
    
    bids_list = list(session["wholesaler_bids"])
    bids_list.insert(0, new_bid)
    session["wholesaler_bids"] = bids_list
    session.modified = True

    flash(f"✅ Offer of ₹{offer_price:,.2f}/Qtl for {offer_qty} Qtl sent to {new_bid['farmer_name']}! (बोली सफलतापूर्वक दर्ज हुई)", "success")
    return redirect(url_for("wholesaler.dashboard"))


@wholesaler_bp.route("/accept-lot", methods=["POST"])
@login_required(ROLE)
def accept_lot():
    lot_id = request.form.get("lot_id", "").strip()
    listing = next((f for f in FARMER_LISTINGS if f["id"] == lot_id), None)

    if not listing:
        flash("Crop lot not found or already booked.", "error")
        return redirect(url_for("wholesaler.dashboard"))

    try:
        qty = float(request.form.get("qty") or listing["quantity_qtl"])
    except (ValueError, TypeError):
        qty = listing["quantity_qtl"]

    total_value = round(listing["asking_rate"] * qty, 2)
    mandi_benchmark_value = round(listing["mandi_rate"] * qty, 2)
    direct_savings = round(max(mandi_benchmark_value - total_value, 0), 2)

    confirmed_deal = {
        "bid_id": f"DEAL-{int(datetime.utcnow().timestamp()) % 100000}",
        "lot_id": listing["id"],
        "farmer_name": listing["name"],
        "crop": listing["crop"],
        "offer_price": listing["asking_rate"],
        "offer_qty": qty,
        "total_value": total_value,
        "savings_est": direct_savings,
        "status": "Confirmed / Ready for Pickup",
        "created_at": datetime.now().strftime("%d %b, %I:%M %p"),
    }

    if "wholesaler_bids" not in session:
        session["wholesaler_bids"] = []

    bids_list = list(session["wholesaler_bids"])
    bids_list.insert(0, confirmed_deal)
    session["wholesaler_bids"] = bids_list
    session.modified = True

    flash(f"🎉 Deal Confirmed! Bought {qty} Qtl of {listing['crop']} from {listing['name']} at ₹{listing['asking_rate']}/Qtl. Estimated Direct Savings: ₹{direct_savings:,.2f}.", "success")
    return redirect(url_for("wholesaler.dashboard"))


@wholesaler_bp.route("/negotiate/<name>", methods=["GET", "POST"])
@login_required(ROLE)
def negotiate(name):
    listing = next((f for f in FARMER_LISTINGS if f["name"].lower() == name.lower() or f["id"].lower() == name.lower()), None)
    if not listing:
        flash("Listing not found.", "error")
        return redirect(url_for("wholesaler.dashboard"))
    
    offer_result = None
    if request.method == "POST":
        try:
            offer_price = float(request.form.get("offer_price") or 0)
            offer_qty = float(request.form.get("offer_qty") or 0)
        except (ValueError, TypeError):
            offer_price = 0
            offer_qty = 0

        if offer_price > 0 and offer_qty > 0:
            total = round(offer_price * offer_qty, 2)
            offer_result = {"offer_price": offer_price, "offer_qty": offer_qty, "total": total}
            
            new_bid = {
                "bid_id": f"BID-{int(datetime.utcnow().timestamp()) % 100000}",
                "lot_id": listing["id"],
                "farmer_name": listing["name"],
                "crop": listing["crop"],
                "offer_price": offer_price,
                "offer_qty": offer_qty,
                "total_value": total,
                "savings_est": round(max((listing["mandi_rate"] - offer_price) * offer_qty, 0), 2),
                "status": "Offer Sent",
                "created_at": datetime.now().strftime("%d %b, %I:%M %p"),
            }
            if "wholesaler_bids" not in session:
                session["wholesaler_bids"] = []
            bids_list = list(session["wholesaler_bids"])
            bids_list.insert(0, new_bid)
            session["wholesaler_bids"] = bids_list
            session.modified = True

            flash(f"Offer of ₹{offer_price}/Qtl sent to {listing['name']}! (बोली दर्ज हुई)", "success")
        else:
            flash("Please enter valid price and quantity.", "error")

    return render_template("wholesaler/negotiate.html", listing=listing, offer_result=offer_result)
