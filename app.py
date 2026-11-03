"""FoodLoop - turn canteen surplus into savings.  Run:  streamlit run app.py"""
from datetime import datetime

import pandas as pd
import streamlit as st

import core

st.set_page_config(page_title="FoodLoop", page_icon="♻️", layout="wide")
core.seed_if_empty()
user = st.session_state.get("user")


# ---------------- sidebar: auth + navigation ----------------
with st.sidebar:
    st.title("♻️ FoodLoop")
    if user is None:
        tab_in, tab_up = st.tabs(["Login", "Register"])
        with tab_in:
            with st.form("login"):
                e, p = st.text_input("Email"), st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    u = core.login(e, p)
                    if u:
                        st.session_state["user"] = u
                        st.rerun()
                    st.error("Wrong email or password.")
            st.caption("Demo: student@foodloop.com / student123  |  canteen@foodloop.com / vendor123")
        with tab_up:
            with st.form("register"):
                n, e2 = st.text_input("Name"), st.text_input("Email ")
                p2 = st.text_input("Password ", type="password")
                role = st.selectbox("I am a", ["student", "vendor"])
                code = st.text_input("Referral code (optional)")
                if st.form_submit_button("Create account"):
                    row, msg = core.register(n, e2, p2, role, code)
                    (st.success if row else st.error)(msg)
        pages = ["Home"]
    else:
        st.write(f"Hi, **{user['name']}** ({user['role']})")
        pages = ["Home", "Order Food", "Wallet", "Refer a Friend"] if user["role"] == "student" \
            else ["Home", "Vendor Dashboard"]
        if st.button("Logout"):
            st.session_state.pop("user")
            st.rerun()
    page = st.radio("Go to", pages)


# ---------------- Home ----------------
def home():
    st.header("Good food shouldn't go to waste 🍛")
    imp = core.impact()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portions saved", imp["portions"])
    c2.metric("Food saved (kg)", imp["kg"])
    c3.metric("CO₂ avoided (kg)", imp["co2"])
    c4.metric("Orders completed", imp["orders"])
    st.subheader("Live surplus deals")
    items = core.live_items()
    if items.empty:
        st.info("No surplus right now. Check back soon!")
        return
    show = items[["name", "mrp", "discount_%", "price_now", "group_price", "quantity", "minutes_left"]]
    st.dataframe(show.rename(columns={"price_now": "price now (₹)", "group_price": f"group price (₹, {core.GROUP_MIN_QTY}+)",
                                      "mrp": "MRP (₹)", "minutes_left": "min left"}),
                 hide_index=True, use_container_width=True)
    with st.expander("How our dynamic discount works"):
        st.table(pd.DataFrame({"Time remaining": ["3 hours", "2 hours", "1 hour", "30 minutes"],
                               "Discount": ["15%", "25%", "40%", "50%"]}))


# ---------------- Student: order ----------------
def order_page():
    st.header("Order surplus food")
    items = core.live_items()
    if items.empty:
        st.info("Nothing available right now.")
        return
    choice = st.selectbox("Choose item", items["name"] + " — " + items["minutes_left"].astype(str) + " min left")
    row = items.iloc[(items["name"] + " — " + items["minutes_left"].astype(str) + " min left").tolist().index(choice)]
    qty = st.number_input("Portions", 1, int(row["quantity"]), 1)
    group = st.checkbox(f"Group deal (needs {core.GROUP_MIN_QTY}+ portions)", disabled=qty < core.GROUP_MIN_QTY)
    unit = row["group_price"] if group and qty >= core.GROUP_MIN_QTY else row["price_now"]
    subtotal = int(unit * qty)
    cap = core.max_redeemable(user["user_id"], subtotal)
    pts = st.slider("Use wallet points (1 pt = ₹1)", 0, max(cap, 0), 0) if cap > 0 else 0
    st.write(f"MRP ₹{int(row['mrp'])} → **₹{int(unit)}** each | Subtotal ₹{subtotal} | Points −₹{pts}")
    st.subheader(f"Total: ₹{subtotal - pts}")
    if st.button("Place order", type="primary"):
        res, msg = core.place_order(user["user_id"], int(row["item_id"]), int(qty), pts, group and qty >= core.GROUP_MIN_QTY)
        if res:
            st.success(f"{msg}  Order #{res['order_id']} | You earned {res['earned']} points 🎉")
            st.balloons()
        else:
            st.error(msg)


# ---------------- Student: wallet ----------------
def wallet_page():
    st.header("💰 FoodLoop Wallet")
    w = core.wallet_summary(user["user_id"])
    a, b, c = st.columns(3)
    a.metric("Available points", w["balance"])
    b.metric("Total earned", w["earned"])
    c.metric("Total redeemed", w["redeemed"])
    st.subheader("Transaction history")
    st.dataframe(w["history"], hide_index=True, use_container_width=True)
    st.subheader("My orders")
    o = core.read("orders")
    st.dataframe(o[o["user_id"] == user["user_id"]], hide_index=True, use_container_width=True)


def referral_page():
    st.header("🤝 Refer a friend")
    st.write(f"Share your code. When a new student registers with it and completes their first "
             f"purchase, **both of you get {core.REFERRAL_BONUS} points**.")
    st.code(user["ref_code"])


# ---------------- Vendor ----------------
def vendor_page():
    st.header("Canteen dashboard")
    t1, t2, t3 = st.tabs(["Add surplus", "Waste forecast", "Sales"])
    with t1:
        with st.form("add"):
            name = st.text_input("Item name")
            mrp = st.number_input("MRP (₹)", 1, 2000, 80)
            qty = st.number_input("Portions", 1, 500, 10)
            hrs = st.slider("Valid for (hours)", 0.5, 6.0, 2.0, 0.5)
            if st.form_submit_button("Publish") and name:
                core.add_item(user["user_id"], name, mrp, qty, hrs)
                st.success("Listed! Price drops automatically as time runs out.")
        live = core.live_items()
        if len(live):
            st.dataframe(live[["name", "mrp", "quantity", "minutes_left", "discount_%", "price_now"]],
                         hide_index=True, use_container_width=True)
    with t2:
        f = core.forecast()
        if f.empty:
            st.info("Not enough history yet.")
        else:
            for msg in f["advice"]:
                st.info("💡 " + msg)
            st.dataframe(f, hide_index=True, use_container_width=True)
    with t3:
        o = core.read("orders")
        if o.empty:
            st.info("No orders yet.")
        else:
            st.metric("Revenue from surplus (₹)", int(o["total_paid"].sum()))
            st.bar_chart(o.groupby("item_name")["qty"].sum())
            st.dataframe(o, hide_index=True, use_container_width=True)


{"Home": home, "Order Food": order_page, "Wallet": wallet_page,
 "Refer a Friend": referral_page, "Vendor Dashboard": vendor_page}[page]()
