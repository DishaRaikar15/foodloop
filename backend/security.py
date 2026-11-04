
import hashlib
import hmac
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
import os


# Load the encryption key from the project's root .env file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_FILE)

PICKUP_KEY = os.getenv("FOODLOOP_PICKUP_KEY")

if not PICKUP_KEY:
    raise RuntimeError(
        "FOODLOOP_PICKUP_KEY is missing. "
        "Check that your project's .env file exists."
    )

try:
    FERNET = Fernet(PICKUP_KEY.encode())
    RAW_KEY = __import__("base64").urlsafe_b64decode(
        PICKUP_KEY.encode()
    )
except Exception as error:
    raise RuntimeError(
        "Invalid FOODLOOP_PICKUP_KEY in .env"
    ) from error


# Derive a separate secret for pickup-code hashing.
HASH_KEY = hmac.new(
    RAW_KEY,
    b"FoodLoop pickup-code verification key",
    hashlib.sha256
).digest()


def generate_pickup_code():
    """Generate a random six-digit pickup code."""

    return f"{secrets.randbelow(900000) + 100000:06d}"


def encrypt_pickup_code(code):
    """Encrypt a pickup code so the student can retrieve it."""

    return FERNET.encrypt(code.encode()).decode()


def decrypt_pickup_code(encrypted_code):
    """Decrypt a stored pickup code."""

    try:
        return FERNET.decrypt(encrypted_code.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        raise ValueError("Unable to retrieve pickup code.")


def hash_pickup_code(order_id, code):
    """Create an order-specific secure verification hash."""

    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise ValueError("Pickup code must contain exactly six digits.")

    message = f"{order_id}:{code}".encode()

    return hmac.new(
        HASH_KEY,
        message,
        hashlib.sha256
    ).hexdigest()


def verify_pickup_code(order_id, code, stored_hash):
    """Verify a code against the specific order."""

    if not stored_hash:
        return False

    try:
        calculated_hash = hash_pickup_code(order_id, code)

        return hmac.compare_digest(
            calculated_hash,
            stored_hash
        )
    except (ValueError, TypeError):
        return False
