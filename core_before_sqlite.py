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
    "items": ["item_id", "vendor_id", "name", "mrp", "quantity", "expires_at", "initial_qty", "history_logged"],
    "orders": ["order_id", "user_id", "item_id", "item_name", "qty", "unit_price",
               "points_used", "total_paid", "group_deal", "created_at", "vendor_id",
               "status", "pickup_code", "collected_at", "cancelled_at", "coupon_code", "coupon_discount"],
    "wallet": ["user_id", "timestamp", "kind", "points", "note"],
    "history": ["date", "weekday", "item", "prepared", "sold", "vendor_id"],
    "reviews": ["review_id", "user_id", "item_id", "order_id", "item_name", "rating", "review", "created_at"],
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
    dtype = {"pickup_code": str} if name == "orders" else None
    df = pd.read_csv(path, keep_default_na=False, dtype=dtype)
    for col in SCHEMAS[name]:
        if col not in df.columns:
            df[col] = ""
    if name == "orders":
        df["status"] = df["status"].fillna("").astype(str).replace({"": "Collected", "nan": "Collected"})
        df["pickup_code"] = df["pickup_code"].map(_pickup_code_str)
    elif name == "items":
        # Backward compatibility for old rows with blank initial_qty
        if len(df):
            orders_df = None
            for idx, r in df.iterrows():
                if str(r.get("initial_qty", "")).strip() == "":
                    curr_qty = int(r["quantity"]) if str(r.get("quantity", "")).isdigit() else 0
                    if (DATA / "orders.csv").exists():
                        if orders_df is None:
                            orders_df = pd.read_csv(DATA / "orders.csv", keep_default_na=False)
                        if not orders_df.empty and "item_id" in orders_df.columns:
                            item_orders = orders_df[(orders_df["item_id"].astype(str) == str(r["item_id"])) & (orders_df["status"] != "Cancelled")]
                            sold_pending = int(item_orders["qty"].astype(int).sum()) if len(item_orders) else 0
                        else:
                            sold_pending = 0
                    else:
                        sold_pending = 0
                    df.at[idx, "initial_qty"] = curr_qty + sold_pending
                if str(r.get("history_logged", "")).strip() == "":
                    df.at[idx, "history_logged"] = 0
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


def get_user(user_id) -> dict | None:
    """Retrieve user dictionary by user_id without app.py accessing CSVs directly."""
    users = read("users")
    match = users[users["user_id"].astype(str) == str(user_id)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


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
    expire_stale_orders()
    items = read("items")
    if items.empty:
        return items
    items["expires_at"] = pd.to_datetime(items["expires_at"])
    items["minutes_left"] = ((items["expires_at"] - datetime.now()).dt.total_seconds() // 60).astype(int)
    items = items[(items["minutes_left"] > 0) & (items["quantity"].astype(int) > 0)].copy()
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
               "expires_at": (datetime.now() + timedelta(hours=validity_hours)).isoformat(timespec="seconds"),
               "initial_qty": quantity, "history_logged": 0}
        save("items", pd.concat([items, pd.DataFrame([row])], ignore_index=True))
        return row, "Listed! Price drops automatically as time runs out."


def vendor_items(vendor_id) -> pd.DataFrame:
    items = read("items")
    return items[items["vendor_id"].astype(str) == str(vendor_id)]


def vendor_orders(vendor_id) -> pd.DataFrame:
    orders = read("orders")
    return orders[orders["vendor_id"].astype(str) == str(vendor_id)]


# ---------------- wallet ----------------
def _log(rows: list[dict]) -> None:
    with _LOCK:
        save("wallet", pd.concat([read("wallet"), pd.DataFrame(rows)], ignore_index=True))


def balance(user_id) -> int:
    w = read("wallet")
    return int(w[w["user_id"].astype(str) == str(user_id)]["points"].sum()) if len(w) else 0


def wallet_summary(user_id) -> dict:
    w = read("wallet")
    w = w[w["user_id"].astype(str) == str(user_id)]
    earned = int(w[w["kind"].isin(["earned", "referral"])]["points"].sum()) if len(w) else 0
    gross_redeemed = -w[w["kind"] == "redeemed"]["points"].sum() if len(w) else 0
    refunded = w[w["kind"] == "refund"]["points"].sum() if len(w) else 0
    net_redeemed = int(gross_redeemed - refunded)
    return {"balance": int(w["points"].sum()) if len(w) else 0,
            "earned": earned,
            "redeemed": max(0, net_redeemed),
            "history": w.sort_values("timestamp", ascending=False)}


# ---------------- ordering ----------------
def max_redeemable(user_id, subtotal: float) -> int:
    return int(min(balance(user_id), subtotal * MAX_REDEEM_SHARE))


def place_order(user_id, item_id, qty, use_points=0, group=False, coupon_code="", coupon_discount=0):
    with _LOCK:
        if qty < 1:
            return None, "Quantity must be at least 1."
        use_points = max(0, use_points)
        users = read("users")
        if not (users["user_id"].astype(str) == str(user_id)).any():
            return None, "Unknown user."
        items = read("items")
        idx = items.index[items["item_id"].astype(str) == str(item_id)]
        if len(idx) == 0:
            return None, "Item not found."
        i = idx[0]
        minutes_left = (pd.to_datetime(items.at[i, "expires_at"]) - datetime.now()).total_seconds() / 60
        if minutes_left <= 0:
            return None, "This offer has expired."
        if qty > int(items.at[i, "quantity"]):
            return None, "Not enough portions available."
        if group and qty < GROUP_MIN_QTY:
            return None, f"Group deals need at least {GROUP_MIN_QTY} portions."

        unit = price_now(items.at[i, "mrp"], minutes_left, group)
        subtotal = unit * qty
        pts = min(int(use_points), max_redeemable(user_id, subtotal))
        coupon_discount = max(0, min(int(coupon_discount), int(subtotal - pts)))
        total = subtotal - pts - coupon_discount
        will_earn = int(total // POINTS_PER_RUPEES)
        now = datetime.now().isoformat(timespec="seconds")
        pickup_code = f"{secrets.randbelow(1_000_000):06d}"

        items.at[i, "quantity"] = int(items.at[i, "quantity"]) - qty
        save("items", items)

        orders = read("orders")
        order = {"order_id": _next_id(orders, "order_id"), "user_id": user_id, "item_id": item_id,
                 "item_name": items.at[i, "name"], "qty": qty, "unit_price": unit,
                 "points_used": pts, "total_paid": total, "group_deal": int(group), "created_at": now,
                 "vendor_id": items.at[i, "vendor_id"], "status": "Pending",
                 "pickup_code": pickup_code, "collected_at": "", "cancelled_at": "",
                 "coupon_code": coupon_code, "coupon_discount": coupon_discount}
        save("orders", pd.concat([orders, pd.DataFrame([order])], ignore_index=True))

        if pts:
            _log([{"user_id": int(user_id), "timestamp": now, "kind": "redeemed", "points": -pts,
                   "note": f"Order #{order['order_id']}"}])
        return {**order, "will_earn": will_earn}, (
            "Order placed! Show your pickup code at the counter.")


def collect_order(order_id, vendor_id, code):
    expire_stale_orders()
    with _LOCK:
        orders = read("orders")
        idx = orders.index[orders["order_id"].astype(str) == str(order_id)]
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
        student_id = int(orders.at[i, "user_id"])
        log = []
        if earned:
            log.append({"user_id": student_id, "timestamp": now, "kind": "earned", "points": earned,
                        "note": f"Order #{orders.at[i, 'order_id']} collected"})

        users = read("users")
        uidx = users.index[users["user_id"].astype(str) == str(student_id)]
        if len(uidx):
            u = uidx[0]
            if int(users.at[u, "first_purchase_done"] or 0) == 0:
                users.at[u, "first_purchase_done"] = 1
                save("users", users)
                ref = users.at[u, "referred_by"]
                if pd.notna(ref) and str(ref).strip() not in ("", "0", "nan", "None"):
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
        idx = orders.index[orders["order_id"].astype(str) == str(order_id)]
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
        iidx = items.index[items["item_id"].astype(str) == str(orders.at[i, "item_id"])]
        if len(iidx):
            items.at[iidx[0], "quantity"] = int(items.at[iidx[0], "quantity"]) + int(orders.at[i, "qty"])
            save("items", items)

        pts = int(orders.at[i, "points_used"] or 0)
        if pts > 0:
            _log([{"user_id": int(orders.at[i, "user_id"]), "timestamp": now, "kind": "refund",
                   "points": pts, "note": f"Order #{orders.at[i, 'order_id']} cancelled"}])
        return orders.iloc[i].to_dict(), "Order cancelled."


def student_orders(user_id) -> pd.DataFrame:
    expire_stale_orders()
    o = read("orders")
    o = o[o["user_id"].astype(str) == str(user_id)]
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
            o = o[o["vendor_id"].astype(str) == str(vendor_id)]
    portions = int(o["qty"].sum()) if len(o) else 0
    kg = portions * KG_PER_PORTION
    return {"portions": portions, "kg": round(kg, 1), "co2": round(kg * CO2_PER_KG, 1),
            "orders": len(o)}


# ---------------- expiry, no-show, history sync ----------------
def expire_stale_orders() -> None:
    """Cancel pending orders whose items have expired without restocking, and refund points."""
    with _LOCK:
        orders = read("orders")
        items = read("items")
        if orders.empty or items.empty:
            sync_history()
            return

        now = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        items_expires = pd.to_datetime(items["expires_at"], errors="coerce")
        expired_item_ids = set(items.loc[items_expires <= now, "item_id"].astype(str))

        if not expired_item_ids:
            sync_history()
            return

        pending_mask = (orders["status"] == "Pending") & (orders["item_id"].astype(str).isin(expired_item_ids))
        if not pending_mask.any():
            sync_history()
            return

        refund_logs = []
        for idx in orders[pending_mask].index:
            orders.at[idx, "status"] = "Cancelled"
            orders.at[idx, "cancelled_at"] = now_iso
            pts = int(orders.at[idx, "points_used"] or 0)
            if pts > 0:
                refund_logs.append({
                    "user_id": int(orders.at[idx, "user_id"]),
                    "timestamp": now_iso,
                    "kind": "refund",
                    "points": pts,
                    "note": f"Order #{orders.at[idx, 'order_id']} cancelled (no-show)"
                })

        save("orders", orders)
        if refund_logs:
            _log(refund_logs)

        sync_history()


def sync_history() -> None:
    """Record historical prepared and sold quantities for expired items into history.csv."""
    with _LOCK:
        items = read("items")
        if items.empty:
            return

        now = datetime.now()
        items_expires = pd.to_datetime(items["expires_at"], errors="coerce")
        mask = (items_expires <= now) & (items["history_logged"].astype(str).str.strip().isin(["0", "", "False"]))
        expired_unlogged = items[mask]
        if expired_unlogged.empty:
            return

        orders = read("orders")
        collected = orders[orders["status"] == "Collected"] if len(orders) else pd.DataFrame()

        history_rows = []
        for idx in expired_unlogged.index:
            r = items.loc[idx]
            exp_dt = pd.to_datetime(r["expires_at"])
            item_id_str = str(r["item_id"])
            prep_val = str(r.get("initial_qty", "")).strip()
            prepared = int(prep_val) if prep_val.isdigit() else int(r["quantity"])

            if not collected.empty:
                col_match = collected[collected["item_id"].astype(str) == item_id_str]
                sold = int(col_match["qty"].astype(int).sum()) if len(col_match) else 0
            else:
                sold = 0

            history_rows.append({
                "date": exp_dt.date().isoformat(),
                "weekday": exp_dt.strftime("%A"),
                "item": r["name"],
                "prepared": prepared,
                "sold": sold,
                "vendor_id": r.get("vendor_id", "")
            })
            items.at[idx, "history_logged"] = 1

        if history_rows:
            history = read("history")
            save("history", pd.concat([history, pd.DataFrame(history_rows)], ignore_index=True))
            save("items", items)


# ---------------- forecasting ----------------
def forecast(weeks: int = 8, vendor_id=None) -> pd.DataFrame:
    """Suggest prep reductions using an exponentially weighted moving average (EWM) of unsold portions.

    Filters history to identical weekdays. For a specific vendor, uses their real history rows,
    falling back to demo history with blank vendor_id only if fewer than 3 real rows exist for that item.
    Computes sample volume, confidence level, trend (latest 3 samples vs earlier samples), and
    calculates suggested cuts capped at average prepared portions.
    """
    h = read("history")
    if h.empty:
        return pd.DataFrame()

    today = datetime.now().strftime("%A")
    h = h[h["weekday"] == today].copy()
    if h.empty:
        return pd.DataFrame()

    h["prepared"] = pd.to_numeric(h["prepared"], errors="coerce").fillna(0).astype(float)
    h["sold"] = pd.to_numeric(h["sold"], errors="coerce").fillna(0).astype(float)
    h["unsold"] = (h["prepared"] - h["sold"]).clip(lower=0)
    h["date"] = pd.to_datetime(h["date"], errors="coerce")

    # Determine candidate items
    if vendor_id is not None:
        v_items = read("items")
        v_active_names = set(v_items.loc[v_items["vendor_id"].astype(str) == str(vendor_id), "name"])
        v_hist_names = set(h.loc[h["vendor_id"].astype(str) == str(vendor_id), "item"])
        candidate_items = sorted(v_active_names | v_hist_names)
        if not candidate_items:
            candidate_items = sorted(h["item"].unique())
    else:
        candidate_items = sorted(h["item"].unique())

    records = []
    for item_name in candidate_items:
        if vendor_id is not None:
            real_rows = h[(h["item"] == item_name) & (h["vendor_id"].astype(str) == str(vendor_id))]
            if len(real_rows) >= 3:
                item_df = real_rows
                source = "real"
            else:
                demo_rows = h[(h["item"] == item_name) & (h["vendor_id"].astype(str).str.strip().isin(["", "nan", "None"]))]
                item_df = pd.concat([real_rows, demo_rows], ignore_index=True)
                source = "real" if len(real_rows) > 0 and len(demo_rows) == 0 else "demo"
        else:
            item_df = h[h["item"] == item_name]
            demo_count = (item_df["vendor_id"].astype(str).str.strip().isin(["", "nan", "None"])).sum()
            source = "demo" if demo_count == len(item_df) else "real"

        if item_df.empty:
            continue

        item_df = item_df.sort_values("date").tail(weeks)
        samples = len(item_df)
        if samples == 0:
            continue

        avg_prepared = round(float(item_df["prepared"].mean()), 1)
        avg_unsold = round(float(item_df["unsold"].mean()), 1)

        # Exponentially weighted moving average of unsold quantity
        ewm_unsold = float(item_df["unsold"].ewm(span=samples, adjust=False).mean().iloc[-1])

        # Confidence based on sample depth
        if samples >= 6:
            confidence = "High"
        elif samples >= 3:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Trend analysis: compare latest 3 samples against prior samples
        if samples >= 4:
            latest_3 = item_df["unsold"].tail(3).mean()
            earlier = item_df["unsold"].iloc[:-3].mean()
            diff = latest_3 - earlier
            if diff > 1.0:
                trend = "rising"
            elif diff < -1.0:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Suggested reduction calculation
        raw_cut = round(0.8 * ewm_unsold)
        cut = min(raw_cut, int(round(avg_prepared)))
        if confidence == "Low" and avg_unsold < 0.10 * avg_prepared:
            cut = 0
        suggested_cut = max(0, int(cut))

        # Advice mentions weekday and confidence level
        if suggested_cut >= 2:
            advice = f"Based on previous {today}s ({confidence} confidence), prepare {suggested_cut} fewer portions of {item_name}."
        else:
            advice = f"{item_name}: Current quantity looks right for {today}s ({confidence} confidence)."

        records.append({
            "item": item_name,
            "avg_prepared": avg_prepared,
            "avg_unsold": avg_unsold,
            "suggested_cut": suggested_cut,
            "confidence": confidence,
            "trend": trend,
            "samples": samples,
            "source": source,
            "advice": advice,
        })

    if not records:
        return pd.DataFrame()

    out_df = pd.DataFrame(records)
    return out_df.sort_values("suggested_cut", ascending=False).reset_index(drop=True)


# ---------------- reusable food menu and demo data ----------------
_DEMO_VENDOR_EMAIL = "canteen@foodloop.com"

FOOD_MENU = {
    "Meals": [
        "Veg Thali", "North Indian Meals", "Veg Biryani", "Paneer Rice Bowl",
        "Chole Bhature", "Veg Pulao",
    ],
    # Keep one roll item so the marketplace does not show repeated photos.
    "Rolls": ["Paneer Roll"],
    "Snacks": [
        "Samosa (2 pcs)", "Vada Pav", "Pav Bhaji", "Veg Sandwich",
        "French Fries", "Bread Pakoda",
    ],
    "South Indian": [
        "Masala Dosa", "Idli (2 pcs)", "Medu Vada", "Uttapam",
    ],
}

FOOD_PRICES = {
    "Veg Thali": 100, "North Indian Meals": 120, "Veg Biryani": 90,
    "Paneer Rice Bowl": 110, "Chole Bhature": 80, "Veg Pulao": 75,
    "Paneer Roll": 80,
    "Samosa (2 pcs)": 30, "Vada Pav": 35, "Pav Bhaji": 70,
    "Veg Sandwich": 50, "French Fries": 60, "Bread Pakoda": 35,
    "Masala Dosa": 60, "Idli (2 pcs)": 35,
    "Medu Vada": 40, "Uttapam": 65,
}

# (name, MRP, available portions, validity in hours)
_DEMO_ITEMS = [
    ("Veg Thali", 100, 12, 2.5),
    ("Paneer Roll", 80, 8, 1.0),
    ("Samosa (2 pcs)", 30, 20, 0.5),
    ("Masala Dosa", 60, 10, 3.5),
    ("North Indian Meals", 120, 8, 2.5),
    ("Veg Biryani", 90, 10, 2.0),
    ("Paneer Rice Bowl", 110, 7, 1.5),
    ("Chole Bhature", 80, 9, 2.0),
    ("Veg Pulao", 75, 10, 1.0),
    ("Vada Pav", 35, 15, 2.0),
    ("Pav Bhaji", 70, 8, 1.5),
    ("Veg Sandwich", 50, 12, 2.5),
    ("French Fries", 60, 10, 1.0),
    ("Bread Pakoda", 35, 10, 2.0),
    ("Idli (2 pcs)", 35, 15, 2.5),
    ("Medu Vada", 40, 12, 1.5),
    ("Uttapam", 65, 8, 1.0),
]


def category_for_item(name: str) -> str:
    """Return a stable category for a menu item or a sensible fallback."""
    item = str(name).strip().lower()
    for category, names in FOOD_MENU.items():
        if item in {n.lower() for n in names}:
            return category
    if any(word in item for word in ("dosa", "idli", "vada", "uttapam")):
        return "South Indian"
    if any(word in item for word in ("roll", "frankie", "wrap")):
        return "Rolls"
    if any(word in item for word in ("samosa", "snack", "fries", "sandwich", "pakoda", "pav")):
        return "Snacks"
    return "Meals"


def ensure_demo_listings() -> None:
    """Add any missing demo listings without deleting vendor-created or existing data."""
    users = read("users")
    match = users[users["email"].astype(str).str.lower() == _DEMO_VENDOR_EMAIL]
    if match.empty:
        return
    vendor_id = int(match.iloc[0]["user_id"])
    with _LOCK:
        items = read("items")
        existing = set(items.loc[items["vendor_id"].astype(str) == str(vendor_id), "name"].astype(str))
        for name, mrp, qty, hrs in _DEMO_ITEMS:
            if name not in existing:
                add_item(vendor_id, name, mrp, qty, hrs)
                existing.add(name)


def reset_demo_listings() -> None:
    """Reset only the demo vendor's listings; other vendors' listings are preserved."""
    users = read("users")
    match = users[users["email"].astype(str).str.lower() == _DEMO_VENDOR_EMAIL]
    if match.empty:
        return
    vendor_id = int(match.iloc[0]["user_id"])
    with _LOCK:
        items = read("items")
        save("items", items[items["vendor_id"].astype(str) != str(vendor_id)])
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
                         "item": item, "prepared": prepared, "sold": sold,
                         "vendor_id": ""})
    save("history", pd.DataFrame(rows))


# ---------------- Cart, coupons, and reviews ----------------
COUPONS = {
    "SAVE10": {"type": "percent", "value": 10, "min_bill": 50, "description": "10% off orders above ₹50"},
    "FOODLOOP20": {"type": "flat", "value": 20, "min_bill": 100, "description": "₹20 off orders above ₹100"},
    "RESCUE15": {"type": "percent", "value": 15, "min_bill": 150, "description": "15% off orders above ₹150"},
}

def coupon_discount(code, subtotal):
    code = str(code or "").strip().upper()
    offer = COUPONS.get(code)
    if not offer:
        return 0, "Invalid coupon code."
    if float(subtotal) < offer["min_bill"]:
        return 0, f"This coupon requires a minimum cart value of ₹{offer['min_bill']}."
    amount = (float(subtotal) * offer["value"] / 100 if offer["type"] == "percent" else offer["value"])
    return min(int(round(amount)), int(subtotal)), f"{code} applied successfully."

def place_cart_order(user_id, cart_items, use_points=0, coupon_code=""):
    """Place all cart lines under one locked operation; roll back CSV state on failure."""
    with _LOCK:
        if not cart_items:
            return [], "Your cart is empty."
        items_before = read("items").copy()
        orders_before = read("orders").copy()
        wallet_before = read("wallet").copy()
        live = live_items()
        subtotal = 0
        normalized = []
        for item_id, qty in cart_items.items():
            match = live[live["item_id"].astype(str) == str(item_id)]
            if match.empty:
                return [], f"An item in your cart is no longer available (item {item_id})."
            row = match.iloc[0]
            qty = int(qty)
            if qty < 1 or qty > int(row["quantity"]):
                return [], f"Not enough portions remain for {row['name']}."
            group = qty >= GROUP_MIN_QTY
            unit = int(row["group_price"] if group else row["price_now"])
            line_total = unit * qty
            subtotal += line_total
            normalized.append((int(item_id), qty, group, line_total))
        discount, msg = coupon_discount(coupon_code, subtotal) if coupon_code else (0, "")
        if coupon_code and not discount:
            return [], msg
        points = min(max(0, int(use_points)), max_redeemable(user_id, subtotal - discount))
        # Allocate coupon and wallet reductions proportionally across line items.
        reductions = discount + points
        remaining_reduction = reductions
        created = []
        for pos, (item_id, qty, group, line_total) in enumerate(normalized):
            allocated = min(line_total, round(reductions * line_total / subtotal)) if subtotal else 0
            if pos == len(normalized) - 1:
                allocated = min(line_total, remaining_reduction)
            remaining_reduction -= allocated
            coupon_part = min(allocated, max(0, discount))
            points_part = allocated - coupon_part
            # Distribute remaining discount first; each order stores the breakdown.
            if coupon_part > discount:
                points_part += coupon_part - discount
                coupon_part = discount
            discount -= coupon_part
            res, error = place_order(user_id, item_id, qty, points_part, group, coupon_code, coupon_part)
            if not res:
                save("items", items_before); save("orders", orders_before); save("wallet", wallet_before)
                return [], error
            created.append(res)
        return created, "Cart order placed successfully."

def add_review(user_id, order_id, rating, review_text=""):
    orders = student_orders(user_id)
    match = orders[orders["order_id"].astype(str) == str(order_id)] if len(orders) else orders
    if match.empty or str(match.iloc[0]["status"]) != "Collected":
        return False, "You can review an order only after it has been collected."
    reviews = read("reviews")
    if (reviews["order_id"].astype(str) == str(order_id)).any():
        return False, "This order has already been reviewed."
    row = match.iloc[0]
    new = {"review_id": _next_id(reviews, "review_id"), "user_id": user_id, "item_id": row["item_id"],
           "order_id": order_id, "item_name": row["item_name"], "rating": int(rating),
           "review": str(review_text or "").strip(), "created_at": datetime.now().isoformat(timespec="seconds")}
    save("reviews", pd.concat([reviews, pd.DataFrame([new])], ignore_index=True))
    return True, "Thank you. Your review has been submitted."

def item_reviews(item_id):
    reviews = read("reviews")
    return reviews[reviews["item_id"].astype(str) == str(item_id)].sort_values("created_at", ascending=False)

def item_rating_summary(item_id):
    reviews = item_reviews(item_id)
    if reviews.empty:
        return 0.0, 0
    return round(float(pd.to_numeric(reviews["rating"], errors="coerce").mean()), 1), len(reviews)
