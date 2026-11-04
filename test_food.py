
from datetime import datetime, timedelta

from backend.auth import register_user
from backend.database import get_connection
from backend.food import (
    add_food_item,
    get_available_food,
    get_vendor_food,
    update_food_item,
    delete_food_item
)

# Create or retrieve a test vendor
email = "testvendor@foodloop.com"

conn = get_connection()
vendor = conn.execute(
    "SELECT user_id FROM users WHERE email = ?",
    (email,)
).fetchone()
conn.close()

if vendor:
    vendor_id = vendor["user_id"]
else:
    user, message = register_user(
        name="Test Vendor",
        email=email,
        password="vendor12345",
        role="vendor"
    )
    print("Vendor registration:", message)
    vendor_id = user["user_id"]

# Set expiry to tomorrow
expiry = (datetime.now() + timedelta(days=1)).strftime(
    "%Y-%m-%d %H:%M"
)

# 1. Add food
success, message = add_food_item(
    vendor_id,
    "Vegetable Sandwich",
    80,
    10,
    expiry
)
print("\nAdd food:", message)

# Get the newly added item
items = get_vendor_food(vendor_id)
print("Vendor food listings:", items)

if items:
    item_id = items[0]["item_id"]

    # 2. View available food
    print("\nAvailable food:", get_available_food())

    # 3. Update food
    success, message = update_food_item(
        vendor_id,
        item_id,
        "Cheese Sandwich",
        90,
        8,
        expiry
    )
    print("\nUpdate food:", message)

    # 4. Delete food
    success, message = delete_food_item(vendor_id, item_id)
    print("Delete food:", message)

    print("Final vendor listings:", get_vendor_food(vendor_id))
