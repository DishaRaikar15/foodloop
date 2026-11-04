
# FoodLoop – Backend Guide

## 1. Project Overview

FoodLoop is a circular food-rescue platform that helps reduce food waste by connecting students with affordable surplus food from campus vendors.

The backend is developed using Python and SQLite.

It supports user authentication, food listings, dynamic pricing, ordering, wallet rewards, referrals, analytics, demand prediction and achievements.

## 2. Technologies Used

- Python 3.13
- SQLite – Database
- Flask – Available for API development if required
- Streamlit – Frontend integration
- Pandas – Data handling

## 3. Backend Folder Structure

```text
foodloop/
│
├── app.py
├── core.py
├── foodloop.db
├── requirements.txt
│
├── backend/
│   ├── __init__.py
│   ├── database.py
│   ├── auth.py
│   ├── food.py
│   ├── pricing.py
│   ├── order.py
│   ├── wallet.py
│   ├── referrals.py
│   ├── analytics.py
│   ├── prediction.py
│   └── rewards.py
│
└── tests/
    └── (backend test files)
```

## 4. Backend Modules

### 4.1 Database – database.py

Responsible for database connections and table initialization.

Main functions:
- `get_connection()`
- `initialize_database()`

Database tables:
- users
- food_items
- orders
- wallet_transactions
- food_history

### 4.2 Authentication – auth.py

Handles student and vendor registration and login.

Main functions:
- `register_user(name, email, password, role, referral_code)`
- `login_user(email, password)`
- `get_user_by_id(user_id)`

Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, not plain text.

### 4.3 Food Management – food.py

Allows vendors to manage surplus food listings.

Main functions:
- `add_food_item(vendor_id, name, mrp, quantity, expires_at)`
- `get_available_food()`
- `get_vendor_food(vendor_id)`
- `update_food_item(vendor_id, item_id, name, mrp, quantity, expires_at)`
- `delete_food_item(vendor_id, item_id)`

### 4.4 Dynamic Pricing – pricing.py

Calculates discounts based on food expiry time and order quantity.

Main function:
- `calculate_price(mrp, expires_at, quantity)`

Discount features:
- Expiry-based discounts
- Group purchase discounts

### 4.5 Order Management – order.py

Handles student orders and vendor collection.

Main functions:
- `place_order(user_id, item_id, quantity)`
- `get_student_orders(user_id)`
- `get_vendor_orders(vendor_id)`
- `mark_order_collected(vendor_id, order_id)`
- `cancel_order(user_id, order_id)`

Features:
- Stock reduction after ordering
- Stock restoration after cancellation
- Automatic wallet and referral reward processing after collection
- Wallet point refunds on cancellation

### 4.6 Wallet – wallet.py

Manages student reward points.

Main functions:
- `get_wallet_balance(user_id)`
- `earn_points(user_id, order_id)`
- `redeem_points(user_id, order_id, points_to_use)`
- `get_wallet_history(user_id)`

Students earn 1 point for every ₹10 paid.

Wallet redemption is limited to 50% of the order bill.

### 4.7 Referral System – referrals.py

Rewards students for referring new users.

Main function:
- `award_referral_bonus(user_id, order_id)`

Referral rewards:
- 20 points for the referring student.
- 20 points for the newly referred student.

Bonuses are awarded after the referred student's first successful food collection.

### 4.8 Impact Analytics – analytics.py

Calculates the environmental impact of rescued food.

Main functions:
- `get_foodloop_impact()`
- `get_vendor_impact(vendor_id)`

Metrics:
- Total rescued food portions
- Completed orders
- Vendor revenue
- Estimated food waste reduction
- Estimated CO₂ equivalent savings

Current calculation assumptions:
- 1 portion = 0.4 kg food
- 1 kg rescued food = 2.5 kg estimated CO₂e savings

These are project estimates, not directly measured environmental outcomes.

### 4.9 Demand Prediction – prediction.py

Records food preparation and sales history and predicts future demand.

Main functions:
- `record_food_history(vendor_id, item, prepared, sold, record_date)`
- `predict_food_demand(vendor_id, item, prepared_quantity, target_date)`

The current prediction method calculates average sales from the last 8 records for the same weekday and food item.

It is a statistical baseline, not a trained machine-learning model.

### 4.10 Rewards – rewards.py

Tracks student achievements and collection streaks.

Main function:
- `get_user_rewards(user_id)`

Achievements:
- First Rescue
- Food Saver
- Super Saver
- Regular Rescuer
- 3-Day Streak

## 5. Frontend Integration

The frontend is developed using Streamlit.

Backend functions can be imported directly into the Streamlit application.

Example:

```python
from backend.auth import login_user
from backend.food import get_available_food
from backend.order import place_order, get_student_orders
from backend.wallet import get_wallet_balance
from backend.rewards import get_user_rewards
from backend.analytics import get_foodloop_impact
```

Example: Display available food.

```python
food_items = get_available_food()

for item in food_items:
    print(item)
```

Example: Display wallet balance.

```python
balance = get_wallet_balance(user_id)
print("Wallet points:", balance)
```

Example: Display student achievements.

```python
rewards = get_user_rewards(user_id)
print(rewards)
```

## 6. Running the Backend

Activate the virtual environment and initialize the database if necessary.

```powershell
py -3.13 backend/database.py
```

Run the Streamlit frontend:

```powershell
py -3.13 -m streamlit run app.py
```

## 7. Testing

Backend tests are maintained separately from production modules.

Run individual tests using:

```powershell
py -3.13 test_auth.py
py -3.13 test_food.py
py -3.13 test_pricing.py
py -3.13 test_order.py
py -3.13 test_wallet.py
py -3.13 test_referrals.py
py -3.13 test_analytics.py
py -3.13 test_prediction.py
py -3.13 test_rewards.py
py -3.13 test_order_integration.py
py -3.13 test_referral_integration.py
```

## 8. Future Improvements

- Machine-learning-based food demand prediction
- Improved vendor analytics dashboard
- Secure payment gateway integration
- REST API for independent frontend/backend deployment
- Automated notifications for expiring food
- More advanced fraud prevention

---

**FoodLoop – Save Food. Save Money. Build a Sustainable Campus.**
