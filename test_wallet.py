
from datetime import datetime, timedelta

from backend.database import get_connection
from backend.food import add_food_item, get_vendor_food
from backend.order import place_order, mark_order_collected
from backend.wallet import (
    get_wallet_balance,
    earn_points,
    redeem_points,
    get_wallet_history
)

# Get existing test accounts
conn = get_connection()

student = conn.execute(
    "SELECT user_id FROM users WHERE email = ?",
    ("teststudent@foodloop.com",)
).fetchone()

vendor = conn.execute(
    "SELECT user_id FROM users WHERE email = ?",
    ("testvendor@foodloop.com",)
).fetchone()

conn.close()

if not student or not vendor:
    print("Test student or vendor account not found.")
    raise SystemExit

student_id = student["user_id"]
vendor_id = vendor["user_id"]

expiry = (
    datetime.now() + timedelta(hours=4)
).strftime("%Y-%m-%d %H:%M")

# Add food for testing
success, message = add_food_item(
    vendor_id, "Wallet Test Meal", 100, 10, expiry
)
print("Food listing:", message)

if not success:
    raise SystemExit

items = get_vendor_food(vendor_id)
item_id = items[0]["item_id"]

# Place first order
order, message = place_order(student_id, item_id, 2)
print("\nFirst order:", message)

if order:
    # Mark order as collected using the secure pickup code
    success, message = mark_order_collected(
        vendor_id,
        order["order_id"],
        order["pickup_code"]
    )
    print("Collection:", message)

    # Try earning points again to test duplicate prevention
    success, message = earn_points(
        student_id, order["order_id"]
    )
    print("Duplicate earn attempt:", message)

    print("Wallet balance:", get_wallet_balance(student_id))

    # Place a second order
    second_order, message = place_order(
        student_id, item_id, 2
    )
    print("\nSecond order:", message)

    if second_order:
        # Redeem 10 points
        success, message = redeem_points(
            student_id, second_order["order_id"], 10
        )
        print("Redeem points:", message)

        print(
            "Updated wallet balance:",
            get_wallet_balance(student_id)
        )

        print("\nWallet history:")
        for transaction in get_wallet_history(student_id):
            print(transaction)
