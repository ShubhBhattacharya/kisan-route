"""WhatsApp Direct Handshake & Verification Utilities.

Generates a 4-digit numeric verification code for the Kisan Direct Handshake.
"""
import random


def generate_otp() -> str:
    return str(random.randint(1000, 9999))


def verify_otp(expected: str, provided: str) -> bool:
    return bool(expected) and str(expected) == str(provided).strip()
