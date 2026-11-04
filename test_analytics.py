
from backend.database import get_connection
from backend.analytics import (
    get_foodloop_impact,
    get_vendor_impact
)

# Get test vendor
conn = get_connection()

vendor = conn.execute(
    "SELECT user_id FROM users WHERE email = ?",
    ("testvendor@foodloop.com",)
).fetchone()

conn.close()

vendor_id = vendor["user_id"]

# Overall FoodLoop impact
print("===== FOODLOOP IMPACT =====")

impact = get_foodloop_impact()

for key, value in impact.items():
    print(f"{key}: {value}")

# Individual vendor impact
print("\n===== VENDOR IMPACT =====")

vendor_impact = get_vendor_impact(vendor_id)

for key, value in vendor_impact.items():
    print(f"{key}: {value}")
