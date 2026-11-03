"""FoodLoop core logic: storage, pricing, wallet, referrals, forecasting.
Storage is plain CSV files managed with pandas (swap for SQLite/Postgres later)."""
from __future__ import annotations

import hashlib
import random
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

SCHEMAS = {
    "users": ["user_id", "name", "email", "password", "role", "ref_code", "referred_by", "first_purchase_done"],
    "items": ["item_id", "vendor_id", "name", "mrp", "quantity", "expires_at"],
    "orders": ["order_id", "user_id", "item_id", "item_name", "qty", "unit_price",
               "points_used", "total_paid", "group_deal", "created_at"],
    "wallet": ["user_id", "timestamp", "kind", "points", "note"],
    "history": ["date", "weekday", "item", "prepared", "sold"],
}

# ---- Business rules (tweak freely) ----
REFERRAL_BONUS = 20          # points to both referrer and new student
POINTS_PER_RUPEES = 10       # earn 1 point per Rs.10 spent
MAX_REDEEM_SHARE = 0.5       # points can cover at most 50% of a bill (1 point = Rs.1)
GROUP_MIN_QTY = 5            # portions needed for a group deal
GROUP_EXTRA_OFF = 0.15       # extra 15% off the time-based price
KG_PER_PORTION = 0.4         # assumption for the impact counter
CO2_PER_KG = 2.5             # kg CO2e avoided per kg food saved (approx.)


# ---------------- storage ----------------
def read(name: str) -> pd.DataFrame:
    path = DATA / f"{name}.csv"
    if not path.exists():
        pd.DataFrame(columns=SCHEMAS[name]).to_csv(path, index=False)
    return pd.read_csv(path, keep_default_na=False)


def save(name: str, df: pd.DataFrame) -> None:
    df.to_csv(DATA / f"{name}.csv", index=False)


def _next_id(df: pd.DataFrame, col: str) -> int:
    return int(df[col].max()) + 1 if len(df) else 1


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()  # use bcrypt/argon2 in production


# ---------------- users ----------------
def register(name, email, password, role="student", referral_code=""):
    users = read("users")
    email = email.strip().lower()
    if not (name and email and password):
        return None, "Please fill all fields."
    if (users["email"] == email).any():
        return None, "Email already registered."
    referrer = ""
    if referral_code.strip():
        match = users[users["ref_code"] == referral_code.strip().upper()]
        if match.empty:
            return None, "Invalid referral code."
        referrer = int(match.iloc[0]["user_id"])
    row = {
        "user_id": _next_id(users, "user_id"), "name": name.strip(), "email": email,
        "password": _hash(password), "role": role,
        "ref_code": "FL" + secrets.token_hex(3).upper(),
        "referred_by": referrer, "first_purchase_done": 0,
    }
    save("users", pd.concat([users, pd.DataFrame([row])], ignore_index=True))
    return row, "Registered successfully!"


def login(email, password):
    users = read("users")
    m = users[(users["email"] == email.strip().lower()) & (users["password"] == _hash(password))]
    return None if m.empty else m.iloc[0].to_dict()


# ---------------- dynamic pricing ----------------
def discount_pct(minutes_left: float) -> int:
    """Time-based discount: the closer to the deadline, the cheaper."""
    if minutes_left <= 0:
        return 0
    if minutes_left <= 30:
        return 50
    if minutes_left <= 60:
        return 40
    if minutes_left <= 120:
        return 25
    if minutes_left <= 180:
        return 15
    return 10


def price_now(mrp: float, minutes_left: float, group: bool = False) -> int:
    p = mrp * (1 - discount_pct(minutes_left) / 100)
    if group:
        p *= 1 - GROUP_EXTRA_OFF
    return round(p)


def live_items() -> pd.DataFrame:
    """Unexpired items with live price columns."""
    items = read("items")
    if items.empty:
        return items
    items["expires_at"] = pd.to_datetime(items["expires_at"])
    items["minutes_left"] = ((items["expires_at"] - datetime.now()).dt.total_seconds() // 60).astype(int)
    items = items[(items["minutes_left"] > 0) & (items["quantity"] > 0)].copy()
    items["discount_%"] = items["minutes_left"].apply(discount_pct)
    items["price_now"] = [price_now(m, t) for m, t in zip(items["mrp"], items["minutes_left"])]
    items["group_price"] = [price_now(m, t, True) for m, t in zip(items["mrp"], items["minutes_left"])]
    return items.sort_values("minutes_left").reset_index(drop=True)


def add_item(vendor_id, name, mrp, quantity, validity_hours):
    items = read("items")
    row = {"item_id": _next_id(items, "item_id"), "vendor_id": vendor_id, "name": name,
           "mrp": mrp, "quantity": quantity,
           "expires_at": (datetime.now() + timedelta(hours=validity_hours)).isoformat(timespec="seconds")}
    save("items", pd.concat([items, pd.DataFrame([row])], ignore_index=True))


# ---------------- wallet ----------------
def _log(rows: list[dict]) -> None:
    save("wallet", pd.concat([read("wallet"), pd.DataFrame(rows)], ignore_index=True))


def balance(user_id) -> int:
    w = read("wallet")
    return int(w[w["user_id"] == user_id]["points"].sum()) if len(w) else 0


def wallet_summary(user_id) -> dict:
    w = read("wallet")
    w = w[w["user_id"] == user_id]
    return {"balance": int(w["points"].sum()) if len(w) else 0,
            "earned": int(w[w["points"] > 0]["points"].sum()) if len(w) else 0,
            "redeemed": int(-w[w["points"] < 0]["points"].sum()) if len(w) else 0,
            "history": w.sort_values("timestamp", ascending=False)}


# ---------------- ordering ----------------
def max_redeemable(user_id, subtotal: float) -> int:
    return int(min(balance(user_id), subtotal * MAX_REDEEM_SHARE))


def place_order(user_id, item_id, qty, use_points=0, group=False):
    items = read("items")
    idx = items.index[items["item_id"] == item_id]
    if len(idx) == 0:
        return None, "Item not found."
    i = idx[0]
    minutes_left = (pd.to_datetime(items.at[i, "expires_at"]) - datetime.now()).total_seconds() / 60
    if minutes_left <= 0:
        return None, "This offer has expired."
    if qty < 1 or qty > items.at[i, "quantity"]:
        return None, "Not enough portions available."
    if group and qty < GROUP_MIN_QTY:
        return None, f"Group deals need at least {GROUP_MIN_QTY} portions."

    unit = price_now(items.at[i, "mrp"], minutes_left, group)
    subtotal = unit * qty
    pts = min(int(use_points), max_redeemable(user_id, subtotal))
    total = subtotal - pts
    earned = int(total // POINTS_PER_RUPEES)
    now = datetime.now().isoformat(timespec="seconds")

    items.at[i, "quantity"] -= qty
    save("items", items)

    orders = read("orders")
    order = {"order_id": _next_id(orders, "order_id"), "user_id": user_id, "item_id": item_id,
             "item_name": items.at[i, "name"], "qty": qty, "unit_price": unit,
             "points_used": pts, "total_paid": total, "group_deal": int(group), "created_at": now}
    save("orders", pd.concat([orders, pd.DataFrame([order])], ignore_index=True))

    log = []
    if pts:
        log.append({"user_id": user_id, "timestamp": now, "kind": "redeemed", "points": -pts,
                    "note": f"Order #{order['order_id']}"})
    if earned:
        log.append({"user_id": user_id, "timestamp": now, "kind": "earned", "points": earned,
                    "note": f"Order #{order['order_id']}"})

    # Referral reward on the new student's FIRST purchase
    users = read("users")
    u = users.index[users["user_id"] == user_id][0]
    if users.at[u, "first_purchase_done"] == 0:
        users.at[u, "first_purchase_done"] = 1
        save("users", users)
        ref = users.at[u, "referred_by"]
        if ref != "":
            log += [{"user_id": user_id, "timestamp": now, "kind": "referral", "points": REFERRAL_BONUS,
                     "note": "Welcome bonus (referred)"},
                    {"user_id": int(ref), "timestamp": now, "kind": "referral", "points": REFERRAL_BONUS,
                     "note": f"Friend {users.at[u, 'name']} made first purchase"}]
    if log:
        _log(log)
    return {**order, "earned": earned}, "Order placed! Show your order ID at the counter."


# ---------------- impact counter ----------------
def impact() -> dict:
    o = read("orders")
    portions = int(o["qty"].sum()) if len(o) else 0
    kg = portions * KG_PER_PORTION
    return {"portions": portions, "kg": round(kg, 1), "co2": round(kg * CO2_PER_KG, 1),
            "orders": len(o)}


# ---------------- forecasting ----------------
def forecast(weeks: int = 8) -> pd.DataFrame:
    """Suggest prep reductions using average unsold quantity on the same weekday."""
    h = read("history")
    if h.empty:
        return pd.DataFrame()
    today = datetime.now().strftime("%A")
    h = h[h["weekday"] == today].copy()
    h["unsold"] = h["prepared"] - h["sold"]
    g = h.sort_values("date").groupby("item").tail(weeks).groupby("item").agg(
        avg_prepared=("prepared", "mean"), avg_unsold=("unsold", "mean")).round(1).reset_index()
    g["suggested_cut"] = (g["avg_unsold"] * 0.8).round().astype(int)
    g["advice"] = g.apply(lambda r: f"Based on previous {today}s, prepare {r.suggested_cut} fewer "
                          f"portions of {r['item']}." if r.suggested_cut >= 2
                          else f"{r['item']}: current quantity looks right.", axis=1)
    return g.sort_values("suggested_cut", ascending=False)


# ---------------- demo data ----------------
def seed_if_empty() -> None:
    if len(read("users")):
        return
    register("Demo Canteen", "canteen@foodloop.com", "vendor123", "vendor")
    register("Demo Student", "student@foodloop.com", "student123", "student")
    for name, mrp, qty, hrs in [("Veg Thali", 100, 12, 2.5), ("Paneer Roll", 80, 8, 1.0),
                                ("Samosa (2 pcs)", 30, 20, 0.5), ("Masala Dosa", 60, 10, 3.5)]:
        add_item(1, name, mrp, qty, hrs)
    rng = random.Random(42)
    rows = []
    for d in range(1, 57):
        day = datetime.now().date() - timedelta(days=d)
        for item, base in [("Veg Thali", 60), ("Paneer Roll", 40), ("Samosa (2 pcs)", 80)]:
            prepared = base + rng.randint(-5, 5)
            extra_waste = 10 if day.strftime("%A") == "Wednesday" else 0
            sold = prepared - rng.randint(0, 6) - extra_waste
            rows.append({"date": day.isoformat(), "weekday": day.strftime("%A"),
                         "item": item, "prepared": prepared, "sold": sold})
    save("history", pd.DataFrame(rows))
