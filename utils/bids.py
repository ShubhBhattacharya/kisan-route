import os
import json
import threading
from datetime import datetime
from config import BASE_DIR

_LOCK = threading.Lock()
_JSON_PATH = os.path.join(BASE_DIR, "kisan_bids.json")
_TMP_JSON_PATH = "/tmp/kisan_bids.json"


def _get_target_path():
    if os.environ.get("VERCEL"):
        return _TMP_JSON_PATH
    return _JSON_PATH


def get_all_bids():
    """Retrieve all bids across wholesalers and farmers (newest first)."""
    # 1. Try DB first
    try:
        from models import Bid
        db_bids = Bid.query.order_by(Bid.id.desc()).all()
        if db_bids:
            return [b.to_dict() for b in db_bids]
    except Exception:
        pass

    # 2. Try JSON file store
    target = _get_target_path()
    with _LOCK:
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass

        # Check secondary path if primary missing
        alt = _JSON_PATH if target != _JSON_PATH else _TMP_JSON_PATH
        if os.path.exists(alt):
            try:
                with open(alt, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass

    return []


def save_bid(bid_dict):
    """Save or update a bid in both DB and persistent JSON storage."""
    if not bid_dict:
        return

    # Ensure required fields
    bid_id = bid_dict.get("bid_id") or f"BID-{int(datetime.utcnow().timestamp()) % 100000}"
    bid_dict["bid_id"] = bid_id
    if "created_at" not in bid_dict:
        bid_dict["created_at"] = datetime.now().strftime("%d %b, %I:%M %p")

    # 1. DB Save
    try:
        from extensions import db
        from models import Bid
        existing = Bid.query.filter_by(bid_id=bid_id).first()
        if existing:
            existing.status = bid_dict.get("status", existing.status)
            existing.offer_price = float(bid_dict.get("offer_price", existing.offer_price))
            existing.offer_qty = float(bid_dict.get("offer_qty", existing.offer_qty))
            existing.total_value = float(bid_dict.get("total_value", existing.total_value))
        else:
            new_b = Bid(
                bid_id=bid_id,
                lot_id=bid_dict.get("lot_id", "LOT-101"),
                farmer_name=bid_dict.get("farmer_name", "Farmer"),
                wholesaler_name=bid_dict.get("wholesaler_name", "Wholesaler"),
                wholesaler_phone=bid_dict.get("wholesaler_phone", "+91 98765 43210"),
                crop=bid_dict.get("crop", "Produce"),
                crop_hi=bid_dict.get("crop_hi", ""),
                offer_price=float(bid_dict.get("offer_price", 0)),
                offer_qty=float(bid_dict.get("offer_qty", 0)),
                total_value=float(bid_dict.get("total_value", 0)),
                savings_est=float(bid_dict.get("savings_est", 0)),
                status=bid_dict.get("status", "Offer Sent"),
                created_at=bid_dict.get("created_at"),
            )
            db.session.add(new_b)
        db.session.commit()
    except Exception as e:
        print("[bids] DB save note:", e)

    # 2. JSON File Save
    with _LOCK:
        bids = []
        target = _get_target_path()
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    bids = json.load(f)
            except Exception:
                bids = []

        # Replace or prepend
        updated = False
        for i, b in enumerate(bids):
            if b.get("bid_id") == bid_id:
                bids[i] = bid_dict
                updated = True
                break
        if not updated:
            bids.insert(0, bid_dict)

        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(bids, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[bids] JSON save note:", e)

    return bid_dict


def update_bid_status(bid_id, new_status):
    """Update status of an existing bid (e.g. 'Accepted by Farmer')."""
    # 1. Update in DB
    try:
        from extensions import db
        from models import Bid
        b = Bid.query.filter_by(bid_id=bid_id).first()
        if b:
            b.status = new_status
            db.session.commit()
    except Exception as e:
        print("[bids] DB status update note:", e)

    # 2. Update in JSON
    with _LOCK:
        target = _get_target_path()
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    bids = json.load(f)
                for item in bids:
                    if item.get("bid_id") == bid_id:
                        item["status"] = new_status
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(bids, f, ensure_ascii=False, indent=2)
            except Exception:
                pass


def get_farmer_incoming_bids(farmer_name=None, crop=None):
    """Get bids meant for the farmer dashboard.
    If farmer is Demo Farmer or name matches or crop matches, return relevant bids.
    Always includes all recent wholesaler bids if specific match is empty,
    ensuring Demo Farmer can test and review any wholesaler's bid immediately.
    """
    all_bids = get_all_bids()
    if not all_bids:
        return []

    # Filter for farmer if specific name or crop matches
    if farmer_name and farmer_name not in ("Demo Farmer", "Farmer", ""):
        matched = [b for b in all_bids if b.get("farmer_name", "").lower() == farmer_name.lower()]
        if matched:
            return matched

    if crop:
        matched = [b for b in all_bids if b.get("crop", "").lower() == crop.lower()]
        if matched:
            return matched

    # For Demo Farmer or overview, return all active bids
    return all_bids
