"""
FoodLoop SQLite Integration Layer
Connects app.py and ui.py to the SQLite backend.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

from backend import auth, food, order, pricing, wallet, analytics
from backend.database import get_connection


# ---------------------------------------------------------
# GENERAL SETTINGS
# ---------------------------------------------------------

DATA = Path(__file__).parent / "data"
DATA.mkdir(parents=True, exist_ok=True)

GROUP_MIN_QTY = 5
REFERRAL_BONUS = 20
POINTS_PER_RUPEES = 10   # 1 point earned per ₹10 spent

COUPONS = {
    "SAVE10": {
        "description": "10% off on orders above ₹50"
    },
    "FOODLOOP20": {
        "description": "₹20 off on orders above ₹100"
    },
    "RESCUE15": {
        "description": "15% off on orders above ₹150"
    }
}


# ---------------------------------------------------------
# DATABASE COMPATIBILITY
# ---------------------------------------------------------

def _ensure_reviews_table():
    """Create the reviews table safely if it does not exist."""

    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                item_id INTEGER,
                item_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                review TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def read(table):
    """Compatibility function for frontend data reads."""

    if table == "reviews":
        _ensure_reviews_table()

    allowed = {
        "reviews",
        "orders",
        "users",
        "food_items",
        "wallet_transactions",
        "food_history"
    }

    if table not in allowed:
        return pd.DataFrame()

    conn = get_connection()

    try:
        return pd.read_sql_query(
            f"SELECT * FROM {table}", conn
        )
    finally:
        conn.close()


def save(table, dataframe):
    """
    CSV-era compatibility function.
    SQLite data must be changed through backend functions.
    """

    raise NotImplementedError(
        "Use the corresponding SQLite backend function instead of save()."
    )


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

def _frontend_user(user):
    """Adapt SQLite user fields to the frontend format."""

    if not user:
        return None

    result = dict(user)
    result["ref_code"] = result.get(
        "referral_code",
        result.get("ref_code", "")
    )
    return result


def register(name, email, password, role="student", code=None):
    user, message = auth.register_user(
        name=name,
        email=email,
        password=password,
        role=role,
        referral_code=code
    )

    return _frontend_user(user), message


def login(email, password):
    user = auth.login_user(email, password)
    return _frontend_user(user)


def get_user(user_id):
    user = auth.get_user_by_id(user_id)
    return _frontend_user(user)


# ---------------------------------------------------------
# FOOD CATEGORIES AND MENU
# ---------------------------------------------------------

def category_for_item(name):
    text = str(name).lower()

    categories = {
        "Breakfast": [
            "idli", "dosa", "upma", "poha", "puri",
            "paratha", "sandwich", "breakfast"
        ],
        "Meals": [
            "meal", "rice", "biryani", "thali", "pulao",
            "roti", "chapati", "dal", "curry"
        ],
        "Snacks": [
            "samosa", "puff", "roll", "vada", "pakoda",
            "noodles", "fries", "burger", "pizza"
        ],
        "Beverages": [
            "tea", "coffee", "juice", "milk", "lassi",
            "shake", "water"
        ],
        "Desserts": [
            "cake", "ice cream", "sweet", "halwa",
            "gulab", "jamun", "dessert"
        ]
    }

    for category, keywords in categories.items():
        if any(word in text for word in keywords):
            return category

    return "Other"


def _load_menu():
    menu = {
        "Breakfast": [
            "Idli",
            "Masala Dosa",
            "Upma",
            "Poha",
            "Puri Bhaji",
            "Paratha",
            "Sandwich",
        ],
        "Meals": [
            "Veg Thali",
            "South Indian Meals",
            "North Indian Meals",
            "Veg Biryani",
            "Paneer Rice",
            "Fried Rice",
            "Dal Khichdi",
        ],
        "Snacks": [
            "Samosa",
            "Veg Puff",
            "Paneer Roll",
            "Vada Pav",
            "French Fries",
            "Burger",
            "Pizza",
        ],
        "Beverages": [
            "Tea",
            "Coffee",
            "Fresh Juice",
            "Lassi",
            "Milkshake",
        ],
        "Desserts": [
            "Gulab Jamun",
            "Cake",
            "Ice Cream",
            "Halwa",
        ],
        "Other": [],
    }

    prices = {
        "Idli": 40,
        "Masala Dosa": 60,
        "Upma": 40,
        "Poha": 35,
        "Puri Bhaji": 50,
        "Paratha": 60,
        "Sandwich": 50,
        "Veg Thali": 100,
        "South Indian Meals": 90,
        "North Indian Meals": 110,
        "Veg Biryani": 100,
        "Paneer Rice": 100,
        "Fried Rice": 80,
        "Dal Khichdi": 70,
        "Samosa": 20,
        "Veg Puff": 25,
        "Paneer Roll": 80,
        "Vada Pav": 25,
        "French Fries": 60,
        "Burger": 80,
        "Pizza": 120,
        "Tea": 15,
        "Coffee": 25,
        "Fresh Juice": 40,
        "Lassi": 40,
        "Milkshake": 60,
        "Gulab Jamun": 40,
        "Cake": 60,
        "Ice Cream": 40,
        "Halwa": 40,
    }

    return menu, prices


FOOD_MENU, FOOD_PRICES = _load_menu()


# ---------------------------------------------------------
# PRICING AND COUPONS
# ---------------------------------------------------------

def discount_pct(minutes_left):
    """Return expiry discount percentage."""

    minutes_left = float(minutes_left)

    if minutes_left <= 0:
        return 0
    elif minutes_left <= 30:
        return 50
    elif minutes_left <= 60:
        return 40
    elif minutes_left <= 120:
        return 25
    elif minutes_left <= 180:
        return 15

    return 10


def price_now(mrp, minutes_left):
    """Calculate current unit price after expiry discount."""

    discount = discount_pct(minutes_left)
    return round(float(mrp) * (1 - discount / 100), 2)


def coupon_discount(code, subtotal):
    """Calculate the discount for a valid coupon."""

    code = str(code or "").strip().upper()
    subtotal = float(subtotal)

    if not code:
        return 0, "No coupon applied."

    if code == "SAVE10" and subtotal >= 50:
        return round(subtotal * 0.10, 2), "10% discount applied!"

    if code == "FOODLOOP20" and subtotal >= 100:
        return 20, "₹20 discount applied!"

    if code == "RESCUE15" and subtotal >= 150:
        return round(subtotal * 0.15, 2), "15% discount applied!"

    if code in COUPONS:
        return 0, "Coupon conditions are not met."

    return 0, "Invalid coupon code."


# ---------------------------------------------------------
# FOOD LISTINGS
# ---------------------------------------------------------

def live_items():
    """Return available food as a frontend-compatible DataFrame."""

    columns = [
        "item_id", "name", "mrp", "quantity",
        "minutes_left", "discount_%", "price_now",
        "group_price", "category"
    ]

    try:
        items = food.get_available_food()
    except Exception:
        return pd.DataFrame(columns=columns)

    result = []

    for item in items:
        try:
            expiry = datetime.fromisoformat(
                item["expires_at"]
            )

            minutes_left = max(
                0,
                (expiry - datetime.now()).total_seconds() / 60
            )

            if minutes_left <= 0:
                continue

            mrp = float(item["mrp"])

            normal_price = pricing.calculate_price(
                mrp, item["expires_at"], 1
            )

            group_price = pricing.calculate_price(
                mrp, item["expires_at"], GROUP_MIN_QTY
            )

            result.append({
                "item_id": item["item_id"],
                "name": item["name"],
                "mrp": mrp,
                "quantity": item["quantity"],
                "minutes_left": round(minutes_left),
                "discount_%": normal_price["expiry_discount"],
                "price_now": normal_price["final_unit_price"],
                "group_price": group_price["final_unit_price"],
                "category": item.get("category") or category_for_item(
                    item["name"]
                )
            })

        except (ValueError, TypeError, KeyError):
            continue

    return pd.DataFrame(result, columns=columns)


def vendor_items(vendor_id):
    """Return a vendor's food listings."""

    items = food.get_vendor_food(vendor_id)
    return pd.DataFrame(items)


def add_item(user_id, name, mrp, qty, hrs, category=None):
    """Add a vendor food listing with an expiry time."""

    try:
        expiry = datetime.now() + timedelta(hours=float(hrs))
        expires_at = expiry.strftime("%Y-%m-%d %H:%M")

        success, message = food.add_food_item(
            vendor_id=user_id,
            name=name,
            mrp=float(mrp),
            quantity=int(qty),
            expires_at=expires_at,
            category=category or category_for_item(name)
        )

        if not success:
            return None, message

        items = food.get_vendor_food(user_id)

        matching = [
            item for item in items
            if item["name"].lower() == name.lower()
        ]

        return (matching[-1] if matching else None), message

    except (ValueError, TypeError):
        return None, "Please enter valid price, quantity and expiry."


def ensure_demo_listings():
    """
    Safe startup compatibility function.
    Does not insert duplicate demo listings into the existing database.
    """
    return None


def seed_if_empty():
    """
    Safe startup compatibility function.
    Does not create demo users or overwrite existing records.
    """
    return None


def reset_demo_listings():
    """
    Deliberately disabled to protect existing food listings.
    """
    return False, "Automatic demo listing reset is disabled to protect your data."


# ---------------------------------------------------------
# WALLET
# ---------------------------------------------------------

def balance(user_id):
    return wallet.get_wallet_balance(user_id)


def wallet_summary(user_id):
    history = wallet.get_wallet_history(user_id)

    earned = sum(
        int(row["points"])
        for row in history
        if row["kind"] == "earned"
    )

    redeemed = sum(
        abs(int(row["points"]))
        for row in history
        if row["kind"] == "redeemed"
    )

    return {
        "balance": wallet.get_wallet_balance(user_id),
        "earned": earned,
        "redeemed": redeemed,
        "history": pd.DataFrame(history)
    }


def max_redeemable(user_id, subtotal):
    available = max(0, int(wallet.get_wallet_balance(user_id)))
    maximum_bill_points = max(0, int(float(subtotal) * 0.50))

    return min(available, maximum_bill_points)


def pending_points(user_id):
    pending = order.get_student_pending_orders(user_id)

    return sum(
        int(float(row["total_paid"]) // POINTS_PER_RUPEES)
        for row in pending
    )


# ---------------------------------------------------------
# ORDERS
# ---------------------------------------------------------

def _frontend_status(status):
    return {
        "placed": "Pending",
        "collected": "Collected",
        "cancelled": "Cancelled",
        "expired": "Expired"
    }.get(status, str(status).title())


def place_order(user_id, item_id, qty, pts=0, group=False):
    result, message = order.place_order(
        user_id=user_id,
        item_id=item_id,
        quantity=qty,
        points_to_use=pts
    )

    if result:
        result["qty"] = result["quantity"]

    return result, message


def place_cart_order(user_id, cart, points=0, coupon=""):
    """Calculate combined cart coupon and submit one transaction."""

    if not cart:
        return None, "Your cart is empty."

    subtotal = 0

    try:
        for item_id, quantity in cart.items():
            item = next(
                (
                    row for row in food.get_available_food()
                    if str(row["item_id"]) == str(item_id)
                ),
                None
            )

            if not item:
                return None, "One or more food items are unavailable."

            calculated = pricing.calculate_price(
                item["mrp"],
                item["expires_at"],
                int(quantity)
            )

            subtotal += calculated["total_price"]

        subtotal = round(subtotal, 2)

        discount, coupon_message = coupon_discount(
            coupon, subtotal
        )

        results, message = order.place_cart_order(
            user_id=user_id,
            cart_items=cart,
            points_to_use=points,
            coupon_discount=discount
        )

        if results:
            return results, message

        return results, f"{message} {coupon_message}"

    except (ValueError, TypeError, KeyError):
        return None, "Unable to calculate your cart. Please refresh and try again."


def student_orders(user_id):
    orders = order.get_student_orders(user_id)

    result = []

    for row in orders:
        item = dict(row)
        item["status"] = _frontend_status(item["status"])
        item["qty"] = item["qty"]
        result.append(item)

    return pd.DataFrame(result)


def vendor_orders(vendor_id):
    orders = order.get_vendor_orders(vendor_id)

    result = []

    for row in orders:
        item = dict(row)
        item["status"] = _frontend_status(item["status"])
        item["qty"] = item["qty"]
        result.append(item)

    return pd.DataFrame(result)


def collect_order(order_id, vendor_id, code):
    return order.mark_order_collected(
        vendor_id=vendor_id,
        order_id=order_id,
        pickup_code=code
    )


def cancel_order(order_id, user_id, user_role):
    if user_role == "vendor":
        return order.cancel_vendor_order(
            vendor_id=user_id,
            order_id=order_id
        )

    if user_role == "student":
        return order.cancel_order(
            user_id=user_id,
            order_id=order_id
        )

    return False, "Invalid user role."


# ---------------------------------------------------------
# IMPACT ANALYTICS
# ---------------------------------------------------------


def impact(vendor_id=None, student_id=None):

    if vendor_id is not None:
        data = analytics.get_vendor_impact(vendor_id)

    elif student_id is not None:
        data = analytics.get_student_impact(student_id)

    else:
        data = analytics.get_foodloop_impact()

    return {
        "portions": data.get("total_portions", 0),
        "kg": data.get("food_rescued_kg", 0),
        "co2": data.get("co2_saved_kg", 0),
        "orders": data.get("total_orders", 0)
    }



# ---------------------------------------------------------
# DEMAND FORECAST
# ---------------------------------------------------------

def forecast(vendor_id=None):
    """Build a simple vendor forecast from recorded food history."""

    columns = ["item", "advice", "confidence", "trend"]

    conn = get_connection()

    try:
        if vendor_id is None:
            rows = conn.execute("""
                SELECT item,
                       SUM(prepared) AS prepared,
                       SUM(sold) AS sold
                FROM food_history
                GROUP BY item
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT item,
                       SUM(prepared) AS prepared,
                       SUM(sold) AS sold
                FROM food_history
                WHERE vendor_id = ?
                GROUP BY item
            """, (vendor_id,)).fetchall()

        results = []

        for row in rows:
            prepared = row["prepared"] or 0
            sold = row["sold"] or 0

            if prepared <= 0:
                continue

            ratio = sold / prepared

            if ratio >= 0.85:
                advice = "High demand — consider preparing more."
                trend = "High"
            elif ratio >= 0.50:
                advice = "Moderate demand — maintain preparation."
                trend = "Moderate"
            else:
                advice = "Low demand — consider preparing less."
                trend = "Low"

            results.append({
                "item": row["item"],
                "advice": advice,
                "confidence": round(ratio * 100, 1),
                "trend": trend
            })

        return pd.DataFrame(results, columns=columns)

    finally:
        conn.close()


# ---------------------------------------------------------
# REVIEWS
# ---------------------------------------------------------

def add_review(user_id, order_id, rating, comment):
    _ensure_reviews_table()

    try:
        rating = int(rating)

        if rating < 1 or rating > 5:
            return False, "Rating must be between 1 and 5."

        conn = get_connection()

        try:
            purchased = conn.execute("""
                SELECT order_id, item_id, item_name
                FROM orders
                WHERE order_id = ?
                  AND user_id = ?
                  AND status = 'collected'
            """, (order_id, user_id)).fetchone()

            if not purchased:
                return False, "Only collected orders can be reviewed."

            conn.execute("""
                INSERT INTO reviews
                (order_id, user_id, item_id, item_name, rating, review)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                user_id,
                purchased["item_id"],
                purchased["item_name"],
                rating,
                str(comment).strip()
            ))

            conn.commit()
            return True, "Review submitted successfully!"

        except Exception as error:
            conn.rollback()

            if "UNIQUE constraint failed" in str(error):
                return False, "You have already reviewed this order."

            raise

        finally:
            conn.close()

    except (ValueError, TypeError):
        return False, "Please enter a valid rating."


def item_reviews(item_id):
    _ensure_reviews_table()

    conn = get_connection()

    try:
        return pd.read_sql_query(
            """
            SELECT * FROM reviews
            WHERE item_id = ?
            ORDER BY created_at DESC
            """,
            conn,
            params=(item_id,)
        )
    finally:
        conn.close()


def item_rating_summary(item_id):
    _ensure_reviews_table()

    conn = get_connection()

    try:
        result = conn.execute("""
            SELECT AVG(rating) AS average_rating,
                   COUNT(*) AS review_count
            FROM reviews
            WHERE item_id = ?
        """, (item_id,)).fetchone()

        return (
            round(result["average_rating"] or 0, 1),
            result["review_count"]
        )

    finally:
        conn.close()