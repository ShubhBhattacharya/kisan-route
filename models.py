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
