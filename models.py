import json
from datetime import datetime

from extensions import db


class User(db.Model):
    """One table for every role (farmer, cluster, customer, driver, wholesaler).

    Fields that only some roles need (Aadhaar, vehicle number, business name,
    etc.) live in `extra_json` instead of as separate columns. This keeps the
    schema simple for a hackathon build while still being real, persisted
    data in SQLite. `get_extra()` / `set_extra()` are just JSON encode/decode
    helpers around that column.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    extra_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("role", "phone", name="uq_role_phone"),
    )

    def set_extra(self, data: dict) -> None:
        self.extra_json = json.dumps(data)

    def get_extra(self) -> dict:
        try:
            return json.loads(self.extra_json or "{}")
        except (TypeError, ValueError):
            return {}

    def __repr__(self):
        return f"<User {self.role}:{self.full_name}>"


class Bid(db.Model):
    """Stores wholesale buyer bids and procurement offers placed on farmer lots."""

    __tablename__ = "bids"

    id = db.Column(db.Integer, primary_key=True)
    bid_id = db.Column(db.String(50), unique=True, index=True)
    lot_id = db.Column(db.String(50), index=True)
    farmer_name = db.Column(db.String(120), index=True)
    wholesaler_name = db.Column(db.String(120))
    wholesaler_phone = db.Column(db.String(20))
    crop = db.Column(db.String(100))
    crop_hi = db.Column(db.String(100))
    offer_price = db.Column(db.Float)
    offer_qty = db.Column(db.Float)
    total_value = db.Column(db.Float)
    savings_est = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="Offer Sent")
    created_at = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "bid_id": self.bid_id,
            "lot_id": self.lot_id,
            "farmer_name": self.farmer_name,
            "wholesaler_name": self.wholesaler_name,
            "wholesaler_phone": self.wholesaler_phone,
            "crop": self.crop,
            "crop_hi": self.crop_hi,
            "offer_price": self.offer_price,
            "offer_qty": self.offer_qty,
            "total_value": self.total_value,
            "savings_est": self.savings_est,
            "status": self.status,
            "created_at": self.created_at or self.timestamp.strftime("%d %b, %I:%M %p"),
        }

    def __repr__(self):
        return f"<Bid {self.bid_id} {self.crop} @ {self.offer_price}>"
