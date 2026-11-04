
from datetime import datetime, timedelta

from backend.pricing import calculate_price

# Test 1: Food expiring in 4 hours
expiry_4_hours = (
    datetime.now() + timedelta(hours=4)
).strftime("%Y-%m-%d %H:%M")

result1 = calculate_price(100, expiry_4_hours, 1)

print("TEST 1: Normal purchase")
print(result1)


# Test 2: Food expiring in 45 minutes
expiry_45_minutes = (
    datetime.now() + timedelta(minutes=45)
).strftime("%Y-%m-%d %H:%M")

result2 = calculate_price(100, expiry_45_minutes, 1)

print("\nTEST 2: Urgent purchase")
print(result2)


# Test 3: Group deal of 5 portions
result3 = calculate_price(100, expiry_45_minutes, 5)

print("\nTEST 3: Group purchase")
print(result3)
