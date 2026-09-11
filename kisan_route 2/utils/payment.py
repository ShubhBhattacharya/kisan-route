"""Mock UPI / online payment simulation. No real money ever moves here."""
import random


def simulate_payment(amount: float, mode: str) -> dict:
    txn_id = f"KR{random.randint(100000, 999999)}"
    return {"status": "success", "txn_id": txn_id, "amount": amount, "mode": mode}
