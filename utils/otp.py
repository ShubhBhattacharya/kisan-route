"""WhatsApp Direct Handshake & Verification Utilities.

Generates a cryptographically secure 4-digit numeric verification code for the Kisan Direct Handshake.
"""
import hmac
import secrets


def generate_otp() -> str:
    """Generate cryptographically secure 4-digit numeric OTP."""
    return str(secrets.randbelow(9000) + 1000)


def verify_otp(expected: str, provided: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    if not expected or not provided:
        return False
    exp_str = str(expected).strip()
    prov_str = str(provided).strip()
    return hmac.compare_digest(exp_str, prov_str)

