
import sqlite3
import secrets
from pathlib import Path

import pandas as pd

from backend.auth import hash_password


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "foodloop.db"
USERS_CSV = ROOT / "data" / "users.csv"
ITEMS_CSV = ROOT / "data" / "items.csv"


def migrate():
    if not DB_PATH.exists():
        raise FileNotFoundError("foodloop.db was not found.")

    if not USERS_CSV.exists() or not ITEMS_CSV.exists():
        raise FileNotFoundError("Required CSV files were not found.")

    users = pd.read_csv(USERS_CSV, keep_default_na=False)
    items = pd.read_csv(ITEMS_CSV, keep_default_na=False)

    required_user_columns = {
        "user_id", "name", "email", "role",
        "ref_code", "referred_by", "first_purchase_done"
    }

    required_item_columns = {
        "item_id", "vendor_id", "name",
        "mrp", "quantity", "expires_at"
    }

    if not required_user_columns.issubset(users.columns):
        raise ValueError("CSV user columns are incomplete.")

    if not required_item_columns.issubset(items.columns):
        raise ValueError("CSV food columns are incomplete.")

    if users["user_id"].duplicated().any():
        raise ValueError("Duplicate user IDs in CSV.")

    if items["item_id"].duplicated().any():
        raise ValueError("Duplicate food IDs in CSV.")

    if users["email"].str.strip().str.lower().duplicated().any():
        raise ValueError("Duplicate emails in CSV.")

    if users["ref_code"].str.strip().str.upper().duplicated().any():
        raise ValueError("Duplicate referral codes in CSV.")

    user_map = {}
    temporary_passwords = {}

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        conn.execute("BEGIN IMMEDIATE")

        existing_emails = {
            row[0].strip().lower()
            for row in conn.execute("SELECT email FROM users")
        }

        existing_codes = {
            row[0].strip().upper()
            for row in conn.execute(
                "SELECT referral_code FROM users"
            )
        }

        for _, user in users.iterrows():
            email = str(user["email"]).strip().lower()
            code = str(user["ref_code"]).strip().upper()

            if email in existing_emails:
                raise ValueError(
                    "An imported account email already exists in SQLite."
                )

            if not code or code in existing_codes:
                raise ValueError(
                    "An imported referral code is empty or already used."
                )

        old_vendor_rows = users[
            users["role"].str.strip().str.lower() == "vendor"
        ]

        if len(old_vendor_rows) != 1:
            raise ValueError(
                "Expected exactly one vendor account in the CSV."
            )

        # Insert vendor first so food listings can reference it.
        ordered_users = pd.concat(
            [
                old_vendor_rows,
                users[
                    users["role"].str.strip().str.lower() != "vendor"
                ]
            ]
        )

        for _, user in ordered_users.iterrows():
            old_id = int(user["user_id"])
            role = str(user["role"]).strip().lower()

            if role not in ("student", "vendor"):
                raise ValueError("Invalid account role in CSV.")

            temporary_password = secrets.token_urlsafe(18)

            referred_by = None
            old_referrer = str(user["referred_by"]).strip()

            if old_referrer:
                old_referrer_id = int(old_referrer)

                if old_referrer_id not in user_map:
                    raise ValueError(
                        "A referral points to an account not yet migrated."
                    )

                referred_by = user_map[old_referrer_id]

            cursor = conn.execute(
                """
                INSERT INTO users (
                    name, email, password_hash, role,
                    referral_code, referred_by, first_purchase_done
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(user["name"]).strip(),
                    str(user["email"]).strip().lower(),
                    hash_password(temporary_password),
                    role,
                    str(user["ref_code"]).strip().upper(),
                    referred_by,
                    int(user["first_purchase_done"] or 0)
                )
            )

            new_id = cursor.lastrowid
            user_map[old_id] = new_id

            temporary_passwords[str(user["name"])] = (
                temporary_password
            )

        # Import food listings using the newly assigned vendor ID.
        for _, item in items.iterrows():
            old_vendor_id = int(item["vendor_id"])

            if old_vendor_id not in user_map:
                raise ValueError(
                    "Food listing references an unknown vendor."
                )

            if not any(
                int(row["user_id"]) == old_vendor_id
                and str(row["role"]).strip().lower() == "vendor"
                for _, row in users.iterrows()
            ):
                raise ValueError(
                    "Food listing owner is not a vendor."
                )

            name = str(item["name"]).strip()
            mrp = float(item["mrp"])
            quantity = int(item["quantity"])
            expiry = str(item["expires_at"]).strip()

            if not name or mrp <= 0 or quantity < 0 or not expiry:
                raise ValueError("Invalid food listing details.")

            conn.execute(
                """
                INSERT INTO food_items (
                    vendor_id, name, mrp, quantity,
                    expires_at, is_active, category, image_url
                )
                VALUES (?, ?, ?, ?, ?, 1, 'Other', NULL)
                """,
                (
                    user_map[old_vendor_id],
                    name,
                    mrp,
                    quantity,
                    expiry
                )
            )

        conn.commit()

        print("\nMIGRATION SUCCESSFUL")
        print("====================")

        print("\nNew account ID mapping:")
        for old_id, new_id in user_map.items():
            print(f"Old ID {old_id} -> New SQLite ID {new_id}")

        print("\nTemporary passwords")
        print("==================")

        for name, password in temporary_passwords.items():
            print(f"{name}: {password}")

        print(
            "\nIMPORTANT: Save these temporary passwords securely. "
            "They are displayed only during this run."
        )

        print("\nImported food listings:", len(items))

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
