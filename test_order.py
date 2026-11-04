
from datetime import datetime, timedelta
from uuid import uuid4

from backend.database import get_connection
from backend.food import add_food_item
from backend.order import place_order, cancel_order
from backend.wallet import get_wallet_balance


print("\n===== FOODLOOP ORDER + WALLET INTEGRATION TEST =====")

# 1. Get existing test student and vendor.
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
    raise Exception("Test student or vendor not found.")

student_id = student["user_id"]
vendor_id = vendor["user_id"]

# 2. Check initial wallet balance.
initial_balance = get_wallet_balance(student_id)

print("\nInitial wallet balance:", initial_balance)

# 3. Add a fresh food item.
expiry = (
    datetime.now() + timedelta(hours=4)
).strftime("%Y-%m-%d %H:%M")

food_name = f"Wallet Test Pizza {uuid4().hex[:6]}"

success, message = add_food_item(
    vendor_id,
    food_name,
    100,
    10,
    expiry
)

if not success:
    raise Exception(f"Food creation failed: {message}")

# Get the exact newly created food item.
conn = get_connection()

item = conn.execute(
    """
    SELECT item_id, quantity
    FROM food_items
    WHERE vendor_id = ? AND name = ?
    ORDER BY item_id DESC
    LIMIT 1
    """,
    (vendor_id, food_name)
).fetchone()

conn.close()

if not item:
    raise Exception("New food item could not be found.")

item_id = item["item_id"]
initial_stock = item["quantity"]

print("\nFood item created:", food_name)
print("Initial stock:", initial_stock)

# 4. Place an order using the maximum allowed wallet points.
points_to_use = 45

order, message = place_order(
    student_id,
    item_id,
    1,
    points_to_use=points_to_use
)

if not order:
    raise Exception(f"Order placement failed: {message}")

order_id = order["order_id"]

print("\nOrder placed successfully!")
print("Order ID:", order_id)
print("Gross bill:", order["gross_total"])
print("Points redeemed:", order["points_used"])
print("Amount paid:", order["total_paid"])

# 5. Verify the 50% redemption limit.
maximum_allowed = int(order["gross_total"] * 0.50)

if order["points_used"] > maximum_allowed:
    raise Exception("Wallet redemption exceeded the 50% limit.")

if order["points_used"] != 45:
    raise Exception("Expected exactly 45 points to be redeemed.")

print("\n50% wallet redemption limit verified!")

# 6. Check wallet balance after checkout.
balance_after_checkout = get_wallet_balance(student_id)

print("Wallet balance after checkout:", balance_after_checkout)

if balance_after_checkout != initial_balance - 45:
    raise Exception("Wallet points were not deducted correctly.")

# 7. Check stock after checkout.
conn = get_connection()

stock_after_order = conn.execute(
    "SELECT quantity FROM food_items WHERE item_id = ?",
    (item_id,)
).fetchone()["quantity"]

conn.close()

print("Stock after checkout:", stock_after_order)

if stock_after_order != initial_stock - 1:
    raise Exception("Stock was not reduced correctly.")

# 8. Cancel the order.
success, message = cancel_order(
    student_id,
    order_id
)

if not success:
    raise Exception(f"Order cancellation failed: {message}")

print("\nCancellation:", message)

# 9. Verify wallet refund.
balance_after_refund = get_wallet_balance(student_id)

print("Wallet balance after refund:", balance_after_refund)

if balance_after_refund != initial_balance:
    raise Exception("Wallet refund was not processed correctly.")

# 10. Verify stock restoration.
conn = get_connection()

stock_after_cancel = conn.execute(
    "SELECT quantity FROM food_items WHERE item_id = ?",
    (item_id,)
).fetchone()["quantity"]

conn.close()

print("Stock after cancellation:", stock_after_cancel)

if stock_after_cancel != initial_stock:
    raise Exception("Stock was not restored correctly.")

print("\n===== ORDER + WALLET INTEGRATION TEST PASSED! =====")
