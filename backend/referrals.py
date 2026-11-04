
from backend.database import get_connection
from backend.order import get_student_orders, mark_order_collected
from backend.wallet import get_wallet_balance

# Find the referred student created by the earlier test
conn = get_connection()

student = conn.execute(
    """
    SELECT user_id, referred_by, email
    FROM users
    WHERE email LIKE 'referraltest%@foodloop.com'
      AND referred_by IS NOT NULL
    ORDER BY user_id DESC
    LIMIT 1
    """
).fetchone()

if not student:
    conn.close()
    print("No existing referral test student found.")
    raise SystemExit

student_id = student["user_id"]
referrer_id = student["referred_by"]

# Find an existing pending order belonging to this student
pending = conn.execute(
    """
    SELECT o.order_id
    FROM orders o
    JOIN food_items f ON o.item_id = f.item_id
    WHERE o.user_id = ?
      AND o.status = 'placed'
    ORDER BY o.order_id DESC
    LIMIT 1
    """,
    (student_id,)
).fetchone()

conn.close()

if not pending:
    print("No pending order found for this referred student.")
    raise SystemExit

order_id = pending["order_id"]

print("Referred student ID:", student_id)
print("Referrer ID:", referrer_id)
print("Existing pending order:", order_id)

# Get the pickup code securely through the student's order history
student_orders = get_student_orders(student_id)

order = next(
    (item for item in student_orders
     if item["order_id"] == order_id),
    None
)

if not order or not order.get("pickup_code"):
    print("Pickup code unavailable. Cannot safely collect this order.")
    raise SystemExit

# Record balances before collection
referrer_before = get_wallet_balance(referrer_id)
student_before = get_wallet_balance(student_id)

print("\nReferrer balance before:", referrer_before)
print("Student balance before:", student_before)

# Collect the order using the correct pickup code
conn = get_connection()
vendor_row = conn.execute(
    """
    SELECT vendor_id
    FROM food_items
    WHERE item_id = ?
    """,
    (order["item_id"],)
).fetchone()
conn.close()

if not vendor_row:
    print("Vendor not found.")
    raise SystemExit

success, message = mark_order_collected(
    vendor_row["vendor_id"],
    order_id,
    order["pickup_code"]
)

print("\nCollection:", message)

# Show balances after collection
referrer_after = get_wallet_balance(referrer_id)
student_after = get_wallet_balance(student_id)

print("\nReferrer balance after:", referrer_after)
print("Student balance after:", student_after)

# Inspect referral transactions for this order
conn = get_connection()

transactions = conn.execute(
    """
    SELECT user_id, points, note, order_id
    FROM wallet_transactions
    WHERE order_id = ?
      AND note LIKE '%Referral bonus%'
    """,
    (order_id,)
).fetchall()

conn.close()

print("\nReferral transactions:")
for transaction in transactions:
    print(dict(transaction))

print("\nNumber of referral bonus transactions:", len(transactions))
