
from backend.database import get_connection
from backend.food import (
    get_vendor_food,
    update_food_item,
    delete_food_item
)

# 1. Get the migrated vendor (Demo Canteen)
conn = get_connection()

vendor = conn.execute(
    "SELECT user_id FROM users WHERE user_id = ?",
    (9,)
).fetchone()

# Find one listing belonging to a different vendor
other_item = conn.execute(
    """
    SELECT item_id, vendor_id
    FROM food_items
    WHERE vendor_id != 9
    LIMIT 1
    """
).fetchone()

conn.close()

if not vendor:
    print("Demo Canteen account not found.")
    raise SystemExit

vendor_id = vendor["user_id"]
print("Demo Canteen vendor ID:", vendor_id)

# 2. Check its own listings
own_items = get_vendor_food(vendor_id)

print("\nOwn listings:")
for item in own_items:
    print(item["item_id"], item["name"])

print("\nOwn listing retrieval:", "PASSED" if all(
    item["vendor_id"] == vendor_id for item in own_items
) else "FAILED")

# 3. Try to update another vendor's listing
if other_item:
    item_id = other_item["item_id"]

    success, message = update_food_item(
        vendor_id,
        item_id,
        "Unauthorized Update",
        100,
        5,
        "2026-11-10 18:00"
    )

    print("\nUnauthorized update:", success, message)

    # 4. Try to delete another vendor's listing
    success, message = delete_food_item(vendor_id, item_id)

    print("Unauthorized delete:", success, message)

    # 5. Verify the other listing still exists
    conn = get_connection()
    unchanged = conn.execute(
        "SELECT name FROM food_items WHERE item_id = ?",
        (item_id,)
    ).fetchone()
    conn.close()

    print(
        "Other vendor's listing preserved:",
        "PASSED" if unchanged else "FAILED"
    )
else:
    print("\nNo other vendor listing found for ownership testing.")
