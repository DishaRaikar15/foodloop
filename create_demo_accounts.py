from backend.auth import register_user, login_user
from backend.database import get_connection

accounts = [
    {
        "name": "FoodLoop Demo Student",
        "email": "student@foodloop.com",
        "password": "student123",
        "role": "student"
    },
    {
        "name": "FoodLoop Demo Canteen",
        "email": "canteen@foodloop.com",
        "password": "vendor123",
        "role": "vendor"
    }
]

for account in accounts:
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT user_id, role FROM users WHERE email = ?",
            (account["email"],)
        ).fetchone()
    finally:
        conn.close()

    if existing:
        print(f"Account already exists: {account['email']}")
        continue

    user, message = register_user(
        account["name"],
        account["email"],
        account["password"],
        account["role"]
    )

    if user:
        print(f"SUCCESS: Created {account['role']} account: {account['email']}")
    else:
        print(f"FAILED: {account['email']} - {message}")

print("Demo account setup completed.")
