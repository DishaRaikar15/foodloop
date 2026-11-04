
from datetime import datetime, timedelta
from uuid import uuid4

from backend.database import get_connection
from backend.auth import register_user
from backend.food import add_food_item
from backend.order import place_order, mark_order_collected, cancel_order


print("\n===== FOODLOOP PICKUP SECURITY TEST =====")

unique_id = uuid4().hex[:8]

# 1. Find existing test student and vendor.
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

print("1. Existing student and vendor found.")

# 2. Create another vendor to test vendor ownership.
other_vendor, message = register_user(
    "Security Test Vendor",
    f"security_vendor_{unique_id}@foodloop.com",
    "Vendor123!",
    "vendor"
)

if not other_vendor:
    raise Exception(f"Second vendor registration failed: {message}")

other_vendor_id = other_vendor["user_id"]

print("2. Second vendor registered.")

# Helper function to create a fresh food item.
def create_test_food(name):
    expiry = (
        datetime.now() + timedelta(hours=4)
    ).strftime("%Y-%m-%d %H:%M")

    success, message = add_food_item(
        vendor_id,
        name,
        100,
        5,
        expiry
    )

    if not success:
        raise Exception(f"Food creation failed: {message}")

    conn = get_connection()

    item = conn.execute(
        """
        SELECT item_id
        FROM food_items
        WHERE vendor_id = ? AND name = ?
        ORDER BY item_id DESC
        LIMIT 1
        """,
        (vendor_id, name)
    ).fetchone()

    conn.close()

    if not item:
        raise Exception("Created food item not found.")

    return item["item_id"]


# 3. Create food and place the first order.
item_id = create_test_food(f"Security Test Meal {unique_id}")

order, message = place_order(student_id, item_id, 1)

if not order:
    raise Exception(f"Order placement failed: {message}")

order_id = order["order_id"]
pickup_code = order["pickup_code"]

print("3. Test order placed successfully.")

# 4. Test incorrect pickup code.
wrong_code = "000000" if pickup_code != "000000" else "000001"

success, message = mark_order_collected(
    vendor_id,
    order_id,
    wrong_code
)

if success:
    raise Exception("SECURITY FAILURE: Incorrect code was accepted.")

print("4. Incorrect pickup code rejected.")

# 5. Test another vendor attempting collection.
success, message = mark_order_collected(
    other_vendor_id,
    order_id,
    pickup_code
)

if success:
    raise Exception("SECURITY FAILURE: Another vendor collected the order.")

print("5. Unauthorized vendor rejected.")

# 6. Test correct pickup code.
success, message = mark_order_collected(
    vendor_id,
    order_id,
    pickup_code
)

if not success:
    raise Exception(f"Correct pickup code rejected: {message}")

print("6. Correct pickup code accepted.")

# 7. Test reuse of the same pickup code.
success, message = mark_order_collected(
    vendor_id,
    order_id,
    pickup_code
)

if success:
    raise Exception("SECURITY FAILURE: Reused pickup code was accepted.")

print("7. Reused pickup code rejected.")

# 8. Create another order to test cancellation.
cancel_item_id = create_test_food(
    f"Cancelled Security Meal {unique_id}"
)

cancel_order_result, message = place_order(
    student_id,
    cancel_item_id,
    1
)

if not cancel_order_result:
    raise Exception(f"Second order placement failed: {message}")

cancel_order_id = cancel_order_result["order_id"]
cancel_pickup_code = cancel_order_result["pickup_code"]

print("8. Second test order placed.")

# 9. Cancel the second order.
success, message = cancel_order(
    student_id,
    cancel_order_id
)

if not success:
    raise Exception(f"Order cancellation failed: {message}")

print("9. Second order cancelled.")

# 10. Try collecting a cancelled order.
success, message = mark_order_collected(
    vendor_id,
    cancel_order_id,
    cancel_pickup_code
)

if success:
    raise Exception("SECURITY FAILURE: Cancelled order was collected.")

print("10. Cancelled order collection rejected.")

print("\n===== ALL PICKUP SECURITY TESTS PASSED! =====")
