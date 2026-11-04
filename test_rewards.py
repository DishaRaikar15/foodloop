
from backend.database import get_connection
from backend.rewards import get_user_rewards

conn = get_connection()

user = conn.execute(
    "SELECT user_id FROM users WHERE email = ?",
    ("teststudent@foodloop.com",)
).fetchone()

conn.close()

if user is None:
    print("Test student not found.")
else:
    rewards = get_user_rewards(user["user_id"])

    print("\n===== FOODLOOP REWARDS =====")

    for key, value in rewards.items():
        print(f"\n{key}: {value}")
