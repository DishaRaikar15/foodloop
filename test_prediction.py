
from datetime import date, timedelta, datetime

from backend.database import get_connection
from backend.prediction import (
    record_food_history,
    predict_food_demand
)

# Get our test vendor
conn = get_connection()

vendor = conn.execute(
    "SELECT user_id FROM users WHERE email = ?",
    ("testvendor@foodloop.com",)
).fetchone()

conn.close()

vendor_id = vendor["user_id"]

# Create a unique test food name
item_name = "Prediction Test " + datetime.now().strftime("%H%M%S")

# Choose a target date one week from today
target_date = date.today() + timedelta(days=7)

print("Food item:", item_name)
print("Prediction date:", target_date)

# Add historical sales for the same weekday
historical_sales = [30, 35, 40]

for weeks_ago, sold_quantity in enumerate(historical_sales, start=1):
    previous_date = target_date - timedelta(days=7 * weeks_ago)

    success, message = record_food_history(
        vendor_id,
        item_name,
        50,
        sold_quantity,
        previous_date.isoformat()
    )

    print(message)

# Predict future demand
prediction = predict_food_demand(
    vendor_id,
    item_name,
    50,
    target_date.isoformat()
)

print("\n===== FOOD DEMAND PREDICTION =====")

for key, value in prediction.items():
    print(f"{key}: {value}")
