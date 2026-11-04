
from datetime import datetime, timedelta

from backend.database import get_connection
from backend.auth import register_user
from backend.food import add_food_item, get_vendor_food
from backend.order import place_order, mark_order_collected
from backend.referrals import award_referral_bonus
from backend.wallet import get_wallet_balance

# Get existing referrer and vendor
conn = get_connection()

referrer = conn.execute(
    "SELECT user_id, referral_code FROM users WHERE email = ?",
    ("teststudent@foodloop.com",)
).fetchone()

vendor = conn.execute(
    "SELECT user_id FROM users WHERE email = ?",
    ("testvendor@foodloop.com",)
).fetchone()

conn.close()

referrer_id = referrer["user_id"]
vendor_id = vendor["user_id"]
referral_code = referrer["referral_code"]

print("Referrer's code:", referral_code)

# Create a new student with a unique email
email = "referraltest" + datetime.now().strftime("%H%M%S") + "@foodloop.com"

new_student, message = register_user(
    name="Referred Student",
    email=email,
    password="student12345",
    role="student",
    referral_code=referral_code
)

print("\nStudent registration:", message)

if new_student:
    new_student_id = new_student["user_id"]

    # Check initial balances
    old_referrer_balance = get_wallet_balance(referrer_id)
    old_student_balance = get_wallet_balance(new_student_id)

    print("Initial referrer balance:", old_referrer_balance)
    print("Initial new student balance:", old_student_balance)

    # Add food
    expiry = (
        datetime.now() + timedelta(hours=4)
    ).strftime("%Y-%m-%d %H:%M")

    success, message = add_food_item(
        vendor_id, "Referral Test Meal", 100, 5, expiry
    )
    print("\nFood listing:", message)

    if success:
        items = get_vendor_food(vendor_id)
        item_id = items[0]["item_id"]

        # Place order
        order, message = place_order(
            new_student_id, item_id, 1
        )
        print("Order:", message)

        if order:
            # Mark food as collected
            success, message = mark_order_collected(
                vendor_id, order["order_id"]
            )
            print("Collection:", message)

            # Award referral bonus
            success, message = award_referral_bonus(
                new_student_id, order["order_id"]
            )
            print("Referral reward:", message)

            # Check final balances
            print("\nFinal referrer balance:",
                  get_wallet_balance(referrer_id))

            print("Final new student balance:",
                  get_wallet_balance(new_student_id))
