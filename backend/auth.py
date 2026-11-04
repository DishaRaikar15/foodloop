
import hashlib
import hmac
import secrets
import sqlite3

from backend.database import get_connection


def hash_password(password):
    """Securely hash a password using PBKDF2."""

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200000
    )

    return salt.hex() + ":" + password_hash.hex()


def verify_password(password, stored_hash):
    """Check whether a password matches its stored hash."""

    try:
        salt_hex, original_hash = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)

        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            200000
        ).hex()

        return hmac.compare_digest(new_hash, original_hash)

    except (ValueError, TypeError):
        return False


def generate_referral_code():
    """Generate a unique referral code."""

    return secrets.token_hex(4).upper()


def register_user(name, email, password, role="student", referral_code=None):
    """Register a new student or vendor."""

    name = name.strip()
    email = email.strip().lower()
    role = role.strip().lower()

    if not name or not email or not password:
        return None, "All fields are required."

    if "@" not in email or "." not in email.split("@")[-1]:
        return None, "Please enter a valid email address."

    if len(password) < 8:
        return None, "Password must contain at least 8 characters."

    if role not in ("student", "vendor"):
        return None, "Invalid account role."

    conn = get_connection()

    try:
        existing_user = conn.execute(
            "SELECT user_id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            return None, "An account with this email already exists."

        referrer_id = None

        if referral_code:
            referrer = conn.execute(
                """
                SELECT user_id FROM users
                WHERE referral_code = ? AND role = 'student'
                """,
                (referral_code.strip().upper(),)
            ).fetchone()

            if not referrer:
                return None, "Invalid referral code."

            referrer_id = referrer["user_id"]

        password_hash = hash_password(password)

        for attempt in range(5):
            new_code = generate_referral_code()

            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users
                    (name, email, password_hash, role,
                     referral_code, referred_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        email,
                        password_hash,
                        role,
                        new_code,
                        referrer_id
                    )
                )

                user_id = cursor.lastrowid
                conn.commit()

                return {
                    "user_id": user_id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "referral_code": new_code
                }, "Registration successful!"

            except sqlite3.IntegrityError:
                conn.rollback()

                existing_user = conn.execute(
                    "SELECT user_id FROM users WHERE email = ?",
                    (email,)
                ).fetchone()

                if existing_user:
                    return None, "An account with this email already exists."

        return None, "Could not generate a referral code. Please try again."

    finally:
        conn.close()


def login_user(email, password):
    """Authenticate a registered user."""

    email = email.strip().lower()

    conn = get_connection()

    try:
        user = conn.execute(
            """
            SELECT user_id, name, email, password_hash,
                   role, referral_code
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if not user:
            return None

        if not verify_password(password, user["password_hash"]):
            return None

        return {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "referral_code": user["referral_code"]
        }

    finally:
        conn.close()


def get_user_by_id(user_id):
    """Get basic user information without exposing the password hash."""

    conn = get_connection()

    try:
        user = conn.execute(
            """
            SELECT user_id, name, email, role, referral_code
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        return dict(user) if user else None

    finally:
        conn.close()
