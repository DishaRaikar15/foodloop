"""FoodLoop core logic: storage, pricing, wallet, referrals, forecasting.
Storage is plain CSV files managed with pandas (swap for SQLite/Postgres later)."""
from __future__ import annotations

import hashlib
import hmac
import os
import random
import re
import secrets
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DATA = Path(os.environ.get("FOODLOOP_DATA", Path(__file__).parent / "data"))
DATA.mkdir(parents=True, exist_ok=True)
_LOCK = threading.RLock()
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ITERS = 200_000

SCHEMAS = {
    "users": ["user_id", "name", "email", "password", "role", "ref_code", "referred_by", "first_purchase_done"],
    "items": ["item_id", "vendor_id", "name", "mrp", "quantity", "expires_at"],
    "orders": ["order_id", "user_id", "item_id", "item_name", "qty", "unit_price",
               "points_used", "total_paid", "group_deal", "created_at", "vendor_id",
               "status", "pickup_code", "collected_at", "cancelled_at"],
    "wallet": ["user_id", "timestamp", "kind", "points", "note"],
    "history": ["date", "weekday", "item", "prepared", "sold"],
}

# ---- Business rules (tweak freely) ----
BASE_DISCOUNT = 0            # discount when more than 180 minutes remain
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
    df = pd.read_csv(path, keep_default_na=False)
    for col in SCHEMAS[name]:
        if col not in df.columns:
            df[col] = ""
    if name == "orders":
        df["status"] = df["status"].replace("", "Collected")
        df["pickup_code"] = df["pickup_code"].map(_pickup_code_str)
    return df


def _pickup_code_str(value) -> str:
    s = str(value).strip()
    if s in ("", "nan", "None"):
        return ""
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s.zfill(6) if s.isdigit() else s


def save(name: str, df: pd.DataFrame) -> None:
    path = DATA / f"{name}.csv"
    fd, tmp = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=DATA)
    os.close(fd)
    try:
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _next_id(df: pd.DataFrame, col: str) -> int:
    return int(df[col].max()) + 1 if len(df) else 1


def _hash(pw: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, _PBKDF2_ITERS)
    return f"pbkdf2${_PBKDF2_ITERS}${salt.hex()}${digest.hex()}"


def _verify(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, hash_hex = str(stored).split("$")
        if algo != "pbkdf2":
            return False
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters_s))
        return hmac.compare_digest(got, bytes.fromhex(hash_hex))
    except (ValueError, TypeError):
        return False


# ---------------- users ----------------
def register(name, email, password, role="student", referral_code=""):
    with _LOCK:
        users = read("users")
        name = (name or "").strip()
        email = (email or "").strip().lower()
        if not name:
            return None, "Name is required."
        if not _EMAIL_RE.match(email):
            return None, "Invalid email format."
        if not password or len(password) < 6:
            return None, "Password must be at least 6 characters."
        if role not in ("student", "vendor"):
            return None, "Role must be student or vendor."
        if (users["email"] == email).any():
            return None, "Email already registered."
        referrer = ""
        if referral_code.strip():
            match = users[users["ref_code"] == referral_code.strip().upper()]
            if match.empty:
                return None, "Invalid referral code."
            referrer = int(match.iloc[0]["user_id"])
        row = {
            "user_id": _next_id(users, "user_id"), "name": name, "email": email,
            "password": _hash(password), "role": role,
            "ref_code": "FL" + secrets.token_hex(3).upper(),
            "referred_by": referrer, "first_purchase_done": 0,
        }
        save("users", pd.concat([users, pd.DataFrame([row])], ignore_index=True))
        return row, "Registered successfully!"


def login(email, password):
    users = read("users")
    m = users[users["email"] == email.strip().lower()]
    if m.empty:
        return None
    row = m.iloc[0]
    if not _verify(password, row["password"]):
        return None
    return row.to_dict()


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
    return BASE_DISCOUNT


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
    with _LOCK:
        name = (name or "").strip()
        if not name:
            return None, "Item name is required."
        if mrp <= 0:
            return None, "MRP must be greater than 0."
        if quantity < 1:
            return None, "Quantity must be at least 1."
        if validity_hours <= 0:
            return None, "Validity must be greater than 0 hours."
        items = read("items")
        row = {"item_id": _next_id(items, "item_id"), "vendor_id": vendor_id, "name": name,
               "mrp": mrp, "quantity": quantity,
               "expires_at": (datetime.now() + timedelta(hours=validity_hours)).isoformat(timespec="seconds")}
        save("items", pd.concat([items, pd.DataFrame([row])], ignore_index=True))
        return row, "Listed! Price drops automatically as time runs out."


def vendor_items(vendor_id) -> pd.DataFrame:
    items = read("items")
    return items[items["vendor_id"] == vendor_id]


def vendor_orders(vendor_id) -> pd.DataFrame:
    orders = read("orders")
    return orders[orders["vendor_id"] == vendor_id]


# ---------------- wallet ----------------
def _log(rows: list[dict]) -> None:
    save("wallet", pd.concat([read("wallet"), pd.DataFrame(rows)], ignore_index=True))


def balance(user_id) -> int:
    w = read("wallet")
    return int(w[w["user_id"] == user_id]["points"].sum()) if len(w) else 0


def wallet_summary(user_id) -> dict:
    w = read("wallet")
    w = w[w["user_id"] == user_id]
    earned = w[w["kind"].isin(["earned", "referral"])]["points"].sum() if len(w) else 0
    redeemed = -w[w["kind"] == "redeemed"]["points"].sum() if len(w) else 0
    return {"balance": int(w["points"].sum()) if len(w) else 0,
            "earned": int(earned),
            "redeemed": int(redeemed),
            "history": w.sort_values("timestamp", ascending=False)}


# ---------------- ordering ----------------
def max_redeemable(user_id, subtotal: float) -> int:
    return int(min(balance(user_id), subtotal * MAX_REDEEM_SHARE))


def place_order(user_id, item_id, qty, use_points=0, group=False):
    with _LOCK:
        if qty < 1:
            return None, "Quantity must be at least 1."
        use_points = max(0, use_points)
        users = read("users")
        if not (users["user_id"] == user_id).any():
            return None, "Unknown user."
        items = read("items")
        idx = items.index[items["item_id"] == item_id]
        if len(idx) == 0:
            return None, "Item not found."
        i = idx[0]
        minutes_left = (pd.to_datetime(items.at[i, "expires_at"]) - datetime.now()).total_seconds() / 60
        if minutes_left <= 0:
            return None, "This offer has expired."
        if qty > items.at[i, "quantity"]:
            return None, "Not enough portions available."
        if group and qty < GROUP_MIN_QTY:
            return None, f"Group deals need at least {GROUP_MIN_QTY} portions."

        unit = price_now(items.at[i, "mrp"], minutes_left, group)
        subtotal = unit * qty
        pts = min(int(use_points), max_redeemable(user_id, subtotal))
        total = subtotal - pts
        will_earn = int(total // POINTS_PER_RUPEES)
        now = datetime.now().isoformat(timespec="seconds")
        pickup_code = f"{secrets.randbelow(1_000_000):06d}"

        items.at[i, "quantity"] -= qty
        save("items", items)

        orders = read("orders")
        order = {"order_id": _next_id(orders, "order_id"), "user_id": user_id, "item_id": item_id,
                 "item_name": items.at[i, "name"], "qty": qty, "unit_price": unit,
                 "points_used": pts, "total_paid": total, "group_deal": int(group), "created_at": now,
                 "vendor_id": items.at[i, "vendor_id"], "status": "Pending",
                 "pickup_code": pickup_code, "collected_at": "", "cancelled_at": ""}
        save("orders", pd.concat([orders, pd.DataFrame([order])], ignore_index=True))

        if pts:
            _log([{"user_id": user_id, "timestamp": now, "kind": "redeemed", "points": -pts,
                   "note": f"Order #{order['order_id']}"}])
        return {**order, "will_earn": will_earn}, (
            "Order placed! Show your pickup code at the counter.")


def collect_order(order_id, vendor_id, code):
    with _LOCK:
        orders = read("orders")
        idx = orders.index[orders["order_id"] == order_id]
        if len(idx) == 0:
            return None, "Order not found."
        i = idx[0]
        if str(orders.at[i, "vendor_id"]) != str(vendor_id):
            return None, "This order is not for your stall."
        if orders.at[i, "status"] != "Pending":
            return None, "Only pending orders can be collected."
        stored = _pickup_code_str(orders.at[i, "pickup_code"]).zfill(6)
        given = _pickup_code_str(code).zfill(6)
        if len(stored) != len(given) or not hmac.compare_digest(stored, given):
            return None, "Invalid pickup code."

        now = datetime.now().isoformat(timespec="seconds")
        orders.at[i, "status"] = "Collected"
        orders.at[i, "collected_at"] = now
        save("orders", orders)

        earned = int(orders.at[i, "total_paid"] // POINTS_PER_RUPEES)
        student_id = orders.at[i, "user_id"]
        log = []
        if earned:
            log.append({"user_id": student_id, "timestamp": now, "kind": "earned", "points": earned,
                        "note": f"Order #{orders.at[i, 'order_id']} collected"})

        users = read("users")
        uidx = users.index[users["user_id"] == student_id]
        if len(uidx):
            u = uidx[0]
            if int(users.at[u, "first_purchase_done"] or 0) == 0:
                users.at[u, "first_purchase_done"] = 1
                save("users", users)
                ref = users.at[u, "referred_by"]
                if ref != "":
                    log += [{"user_id": student_id, "timestamp": now, "kind": "referral",
                             "points": REFERRAL_BONUS, "note": "Welcome bonus (referred)"},
                            {"user_id": int(ref), "timestamp": now, "kind": "referral",
                             "points": REFERRAL_BONUS,
                             "note": f"Friend {users.at[u, 'name']} made first purchase"}]
        if log:
            _log(log)
        return orders.iloc[i].to_dict(), "Order collected."


def cancel_order(order_id, user_id, role):
    with _LOCK:
        orders = read("orders")
        idx = orders.index[orders["order_id"] == order_id]
        if len(idx) == 0:
            return None, "Order not found."
        i = idx[0]
        if orders.at[i, "status"] != "Pending":
            return None, "Only pending orders can be cancelled."
        if role == "student":
            if str(orders.at[i, "user_id"]) != str(user_id):
                return None, "You can only cancel your own orders."
        elif role == "vendor":
            if str(orders.at[i, "vendor_id"]) != str(user_id):
                return None, "You can only cancel orders for your items."
        else:
            return None, "Not allowed to cancel this order."

        now = datetime.now().isoformat(timespec="seconds")
        orders.at[i, "status"] = "Cancelled"
        orders.at[i, "cancelled_at"] = now
        save("orders", orders)

        items = read("items")
        iidx = items.index[items["item_id"] == orders.at[i, "item_id"]]
        if len(iidx):
            items.at[iidx[0], "quantity"] += int(orders.at[i, "qty"])
            save("items", items)

        pts = int(orders.at[i, "points_used"] or 0)
        if pts > 0:
            _log([{"user_id": orders.at[i, "user_id"], "timestamp": now, "kind": "refund",
                   "points": pts, "note": f"Order #{orders.at[i, 'order_id']} cancelled"}])
        return orders.iloc[i].to_dict(), "Order cancelled."


def student_orders(user_id) -> pd.DataFrame:
    o = read("orders")
    o = o[o["user_id"] == user_id]
    if o.empty:
        return o
    return o.sort_values("created_at", ascending=False)


def pending_points(user_id) -> int:
    o = student_orders(user_id)
    o = o[o["status"] == "Pending"]
    if o.empty:
        return 0
    return int((o["total_paid"] // POINTS_PER_RUPEES).sum())


# ---------------- impact counter ----------------
def impact(vendor_id=None) -> dict:
    o = read("orders")
    if len(o):
        o = o[o["status"] == "Collected"]
        if vendor_id is not None:
            o = o[o["vendor_id"] == vendor_id]
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
_DEMO_VENDOR_EMAIL = "canteen@foodloop.com"
_DEMO_ITEMS = [("Veg Thali", 100, 12, 2.5), ("Paneer Roll", 80, 8, 1.0),
               ("Samosa (2 pcs)", 30, 20, 0.5), ("Masala Dosa", 60, 10, 3.5)]


def reset_demo_listings() -> None:
    users = read("users")
    match = users[users["email"] == _DEMO_VENDOR_EMAIL]
    if match.empty:
        return
    vendor_id = int(match.iloc[0]["user_id"])
    with _LOCK:
        items = read("items")
        if len(items):
            save("items", items[items["vendor_id"] != vendor_id])
        for name, mrp, qty, hrs in _DEMO_ITEMS:
            add_item(vendor_id, name, mrp, qty, hrs)


def seed_if_empty() -> None:
    if len(read("users")):
        return
    register("Demo Canteen", "canteen@foodloop.com", "vendor123", "vendor")
    register("Demo Student", "student@foodloop.com", "student123", "student")
    reset_demo_listings()
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
