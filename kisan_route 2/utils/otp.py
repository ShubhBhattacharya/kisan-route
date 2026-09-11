"""Mock OTP system.

Real SMS delivery (via MSG91, Twilio, etc.) can replace `generate_otp`'s
internals later without touching any calling code — callers only see a
4-digit string and a verify function.
"""
import random


def generate_otp() -> str:
    return str(random.randint(1000, 9999))


def verify_otp(expected: str, provided: str) -> bool:
    return bool(expected) and str(expected) == str(provided).strip()
