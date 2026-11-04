
from datetime import datetime, timedelta
from uuid import uuid4

from backend.auth import register_user
from backend.database import get_connection
from backend.order import place_order, mark_order_collected
from backend.wallet import get_wallet_balance


print("\n===== REFERRAL INTEGRATION TEST =====")

unique_id = uuid4().hex[:8]

# 1. Create a referrer student.
referrer, message = register_user(
    "Referrer Student",
    f"referrer_{unique_id}@foodloop.com",
    "Student123!",
    "student"
)

if not referrer:
    raise Exception(f"Referrer registration failed: {message}")

referrer_id = referrer["user_id"]

# Get the referral code.
conn = get_connection()

referral_code = conn.execute(
    "SELECT referral_code FROM users WHERE user_id = ?",
    (referrer_id,)
).fetchone()["referral_code"]

conn.close()

print("1. Referrer registered successfully.")

# 2. Create another student using the referral code.
referred, message = register_user(
    "Referred Student",
    f"referred_{unique_id}@foodloop.com",
    "Student123!",
    "student",
    referral_code=referral_code
)

if not referred:
    raise Exception(f"Referred student registration failed: {message}")

referred_id = referred["user_id"]

print("2. Referred student registered successfully.")

# 3. Create a vendor.
vendor, message = register_user(
    "Referral Test Vendor",
    f"vendor_{unique_id}@foodloop.com",
    "Vendor123!",
    "vendor"
)

if not vendor:
    raise Exception(f"Vendor registration failed: {message}")

vendor_id = vendor["user_id"]

print("3. Vendor registered successfully.")

# 4. Create a food item.
conn = get_connection()

expiry = (datetime.now() + timedelta(days=1)).strftime(
    "%Y-%m-%d %H:%M"
)

cursor = conn.execute(
    """
    INSERT INTO food_items
    (vendor_id, name, mrp, quantity, expires_at, is_active)
    VALUES (?, ?, ?, ?, ?, 1)
    """,
    (vendor_id, "Referral Test Meal", 100, 5, expiry)
)

item_id = cursor.lastrowid

conn.commit()
conn.close()

print("4. Food item created successfully.")

# 5. Referred student places an order.
order, message = place_order(referred_id, item_id, 1)

if not order:
    raise Exception(f"Order placement failed: {message}")

order_id = order["order_id"]
pickup_code = order["pickup_code"]

print("5. Referred student placed an order.")

# 6. Vendor collects the order using the pickup code.
pickup_code = order["pickup_code"]
success, message = mark_order_collected(
    vendor_id, order_id, pickup_code
)

if not success:
    raise Exception(f"Collection failed: {message}")

print("6. Order collected:", message)

# 7. Check both wallet balances.
referrer_balance = get_wallet_balance(referrer_id)
referred_balance = get_wallet_balance(referred_id)

print("\n===== REFERRAL RESULTS =====")
print("Referrer wallet balance:", referrer_balance)
print("Referred student wallet balance:", referred_balance)

# 8. Verify referral bonuses.
if referrer_balance != 20:
    raise Exception("Referrer did not receive exactly 20 bonus points.")

if referred_balance < 20:
    raise Exception("Referred student did not receive the referral bonus.")

# 9. Verify first purchase was recorded.
conn = get_connection()

first_purchase = conn.execute(
    "SELECT first_purchase_done FROM users WHERE user_id = ?",
    (referred_id,)
).fetchone()["first_purchase_done"]

conn.close()

if first_purchase != 1:
    raise Exception("First purchase was not recorded.")

print("\n===== REFERRAL INTEGRATION TEST PASSED! =====")
