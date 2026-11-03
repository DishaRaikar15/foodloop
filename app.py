"""FoodLoop - turn canteen surplus into savings.  Run:  streamlit run app.py"""
from datetime import datetime

import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="FoodLoop", page_icon="♻️", layout="wide")
ui.inject_css()

core.seed_if_empty()
user = st.session_state.get("user")


# ---------------- sidebar: auth + navigation ----------------
with st.sidebar:
    st.title("♻️ FoodLoop")
    if user is None:
        tab_in, tab_up = st.tabs(["Login", "Register"])
        with tab_in:
            with st.form("login"):
                e, p = st.text_input("Email", key="login_email"), st.text_input("Password", type="password", key="login_password")
                if st.form_submit_button("Login"):
                    u = core.login(e, p)
                    if u:
                        st.session_state["user"] = u
                        st.session_state["nav_page"] = "Home"
                        st.rerun()
                    st.error("Wrong email or password.")
            st.caption("Demo: student@foodloop.com / student123  |  canteen@foodloop.com / vendor123")
        with tab_up:
            with st.form("register"):
                n, e2 = st.text_input("Name", key="register_name"), st.text_input("Email", key="register_email")
                p2 = st.text_input("Password", type="password", key="register_password")
                role = st.selectbox("I am a", ["student", "vendor"], key="register_role")
                code = st.text_input("Referral code (optional)", key="register_referral")
                if st.form_submit_button("Create account"):
                    row, msg = core.register(n, e2, p2, role, code)
                    (st.success if row else st.error)(msg)
        pages = ["Home"]
    else:
        st.write(f"Hi, **{user['name']}** ({user['role']})")
        pages = ["Home", "Order Food", "Wallet", "Refer a Friend"] if user["role"] == "student" \
            else ["Home", "Vendor Dashboard"]
        if user["role"] == "vendor":
            with st.expander("Demo"):
                if st.button("Reset demo listings"):
                    core.reset_demo_listings()
                    st.rerun()
        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.session_state["nav_page"] = "Home"
            st.rerun()

    if st.session_state.get("nav_page") not in pages:
        st.session_state["nav_page"] = pages[0]

    page = st.radio("Go to", pages, key="nav_page")


# ---------------- Home ----------------
def home():
    if user and user.get("role") == "student":
        pts = core.balance(user["user_id"])
        ui.hero(f"Hello {user['name']} 👋", f"You have {pts} ⭐ points")
    else:
        ui.hero("Good food shouldn't go to waste 🍛", "Turn campus canteen surplus into delicious, affordable meals")

    imp = core.impact()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portions saved", imp["portions"])
    c2.metric("Food saved (kg)", imp["kg"])
    c3.metric("CO₂ avoided (kg)", imp["co2"])
    c4.metric("Orders collected", imp["orders"])

    st.subheader("Live surplus deals")
    items = core.live_items()
    if items.empty:
        st.info("No surplus right now. Check back soon!")
        return

    # Search & Chip filters
    search_query = st.text_input("Search deals", placeholder="Search by item name (e.g., thali, roll, samosa)...", label_visibility="collapsed")
    filter_opts = ["All", "Ending soon (<60 min)", "Group deals", "Under ₹50"]
    if hasattr(st, "pills"):
        active_filter = st.pills("Filter deals", filter_opts, default="All", label_visibility="collapsed")
    else:
        active_filter = st.radio("Filter deals", filter_opts, horizontal=True, label_visibility="collapsed")
    if not active_filter:
        active_filter = "All"

    filtered = items.copy()
    if search_query and search_query.strip():
        filtered = filtered[filtered["name"].str.contains(search_query.strip(), case=False, na=False)]
    if active_filter == "Ending soon (<60 min)":
        filtered = filtered[filtered["minutes_left"] < 60]
    elif active_filter == "Group deals":
        filtered = filtered[filtered["quantity"] >= core.GROUP_MIN_QTY]
    elif active_filter == "Under ₹50":
        filtered = filtered[filtered["price_now"] < 50]

    if filtered.empty:
        st.info("No items match your filter. Check back soon!")
        return

    # 2-column grid of food cards with Order button
    cols = st.columns(2)
    for i, (_, row) in enumerate(filtered.iterrows()):
        col = cols[i % 2]
        with col:
            ui.food_card(row)
            item_id = int(row["item_id"])
            if user and user.get("role") == "student":
                if st.button("Order", key=f"home_order_{item_id}", width="stretch"):
                    st.session_state["selected_item_id"] = item_id
                    st.session_state["nav_page"] = "Order Food"
                    st.rerun()
            elif user and user.get("role") == "vendor":
                st.caption("Viewing as canteen vendor")
            else:
                if st.button("Order", key=f"home_order_{item_id}", width="stretch"):
                    st.session_state["selected_item_id"] = item_id
                    st.info("Please log in or register as a student in the sidebar to order.")

    with st.expander("How our dynamic discount works"):
        st.table(pd.DataFrame({"Time remaining": ["3 hours", "2 hours", "1 hour", "30 minutes"],
                               "Discount": ["15%", "25%", "40%", "50%"]}))


# ---------------- Student: order ----------------
def order_page():
    ui.hero("Order surplus food 🛒", "Rescue fresh meals before time runs out")
    items = core.live_items()
    if items.empty:
        st.info("Nothing available right now.")
        return

    item_ids = items["item_id"].tolist()
    preselected = st.session_state.pop("selected_item_id", None)
    default_idx = item_ids.index(preselected) if preselected in item_ids else 0

    st.markdown('<div class="fl-card">', unsafe_allow_html=True)
    selected_id = st.selectbox(
        "Choose item", item_ids, index=default_idx,
        format_func=lambda iid: items.loc[items["item_id"] == iid, "name"].iloc[0],
    )
    row = items.loc[items["item_id"] == selected_id].iloc[0]
    qty = st.number_input("Portions", 1, int(row["quantity"]), 1)
    group = st.checkbox(f"Group deal (needs {core.GROUP_MIN_QTY}+ portions)", disabled=qty < core.GROUP_MIN_QTY)
    unit = row["group_price"] if group and qty >= core.GROUP_MIN_QTY else row["price_now"]
    subtotal = int(unit * qty)
    cap = core.max_redeemable(user["user_id"], subtotal)
    pts = st.slider("Use wallet points (1 pt = ₹1)", 0, max(cap, 0), 0) if cap > 0 else 0
    st.write(f"MRP ₹{int(row['mrp'])} → **₹{int(unit)}** each | Subtotal ₹{subtotal} | Points −₹{pts}")
    st.subheader(f"Total: ₹{subtotal - pts}")
    place_order_clicked = st.button("Place order", type="primary", width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    if place_order_clicked:
        res, msg = core.place_order(user["user_id"], int(row["item_id"]), int(qty), pts, group and qty >= core.GROUP_MIN_QTY)
        if res:
            st.success(msg)
            ui.pickup_card(res)
            st.write(f"You'll earn {res['will_earn']} points once you collect your order")
            st.balloons()
        else:
            st.error(msg)


# ---------------- Student: wallet ----------------
def wallet_page():
    flash = st.session_state.pop("_flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])
    w = core.wallet_summary(user["user_id"])
    pending = core.pending_points(user["user_id"])

    ui.hero("FoodLoop Wallet 💰", "Track your eco-points and orders")
    ui.points_chip(w["balance"], pending)

    a, b, c = st.columns(3)
    a.metric("Available points", w["balance"])
    b.metric("Total earned", w["earned"])
    c.metric("Total redeemed", w["redeemed"])

    st.subheader("Transaction history")
    st.dataframe(w["history"], hide_index=True, width="stretch")

    st.subheader("My orders")
    orders = core.student_orders(user["user_id"])
    if orders.empty:
        st.info("No orders yet.")
        return

    status_classes = {
        "Pending": "fl-badge fl-badge-status-pending",
        "Collected": "fl-badge fl-badge-status-collected",
        "Cancelled": "fl-badge fl-badge-status-cancelled",
    }

    for _, row in orders.iterrows():
        oid = int(row["order_id"])
        status = str(row["status"])
        badge_cls = status_classes.get(status, "fl-badge")
        st.markdown(
            f"""
            <div class="fl-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div>
                        <span style="font-size: 1.15rem; font-weight: 800; color: #1F1B2D;">{row['item_name']}</span>
                        <span style="color: #6B7280; font-weight: 600; margin-left: 8px;">&times; {int(row['qty'])}</span>
                    </div>
                    <span class="{badge_cls}">{status}</span>
                </div>
                <div style="display: flex; justify-content: space-between; color: #4B5563; font-size: 0.95rem;">
                    <span>Order #{oid} &bull; {str(row['created_at'])[:16]}</span>
                    <span>Total Paid: <b style="color: #1F1B2D;">₹{int(row['total_paid'])}</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if status == "Pending":
            ui.pickup_card(row.to_dict())
            if st.button("Cancel order", key=f"stu_cancel_{oid}", width="stretch"):
                res, msg = core.cancel_order(oid, user["user_id"], user["role"])
                if res:
                    st.session_state["_flash"] = ("success", msg)
                    st.rerun()
                st.error(msg)


def referral_page():
    ui.hero("Refer a friend 🤝", "Earn rewards together")
    st.write(f"Share your code. When a new student registers with it and completes their first "
             f"purchase, **both of you get {core.REFERRAL_BONUS} points**.")
    st.code(user["ref_code"])


# ---------------- Vendor ----------------
def vendor_page():
    flash = st.session_state.pop("_flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])

    ui.hero("Canteen Dashboard 🏪", f"Logged in as {user['name']}")

    all_orders = core.vendor_orders(user["user_id"])
    collected = all_orders[all_orders["status"] == "Collected"] if len(all_orders) else all_orders
    revenue = int(collected["total_paid"].sum()) if len(collected) else 0
    orders_collected = len(collected)

    live = core.live_items()
    mine = core.vendor_items(user["user_id"])
    live_mine = live[live["item_id"].isin(mine["item_id"])] if len(live) and len(mine) else live.iloc[0:0]
    active_listings = len(live_mine)

    v_imp = core.impact(vendor_id=user["user_id"])
    portions_saved = v_imp["portions"]

    # Metric tiles on top: revenue, orders collected, active listings, portions saved
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Revenue from surplus", f"₹{revenue}")
    m2.metric("Orders collected", orders_collected)
    m3.metric("Active listings", active_listings)
    m4.metric("Portions saved", portions_saved)

    t1, t2, t3, t4 = st.tabs(["Add surplus", "Waste forecast", "Sales", "Orders"])
    with t1:
        with st.form("add"):
            name = st.text_input("Item name")
            mrp = st.number_input("MRP (₹)", 1, 2000, 80)
            qty = st.number_input("Portions", 1, 500, 10)
            hrs = st.slider("Valid for (hours)", 0.5, 6.0, 2.0, 0.5)
            if st.form_submit_button("Publish"):
                row, msg = core.add_item(user["user_id"], name, mrp, qty, hrs)
                if row:
                    st.success(msg)
                else:
                    st.error(msg)
        if len(live_mine):
            st.subheader("Active listings")
            st.dataframe(live_mine[["name", "mrp", "quantity", "minutes_left", "discount_%", "price_now"]],
                         hide_index=True, width="stretch")
    with t2:
        f = core.forecast()
        if f.empty:
            st.info("Not enough history yet.")
        else:
            for msg in f["advice"]:
                st.info("💡 " + msg)
            st.dataframe(f, hide_index=True, width="stretch")
    with t3:
        if collected.empty:
            st.info("No collected orders yet.")
        else:
            st.subheader("Sales per item")
            sales_by_item = collected.groupby("item_name")["qty"].sum()
            st.bar_chart(sales_by_item, color="#FDB913")
            st.subheader("Collected orders")
            st.dataframe(collected, hide_index=True, width="stretch")
    with t4:
        pending = all_orders[all_orders["status"] == "Pending"] if len(all_orders) else all_orders
        if pending.empty:
            st.info("No pending orders.")
        else:
            for _, row in pending.iterrows():
                oid = int(row["order_id"])
                st.markdown(
                    f"""
                    <div class="fl-card">
                        <div style="font-size: 1.1rem; font-weight: 700; color: #1F1B2D;">{row['item_name']} &times; {int(row['qty'])} &mdash; ₹{int(row['total_paid'])}</div>
                        <div style="font-size: 0.85rem; color: #6B7280; margin-top: 2px;">Order #{oid}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                code = st.text_input("Pickup code", key=f"collect_code_{oid}")
                c1, c2 = st.columns(2)
                if c1.button("Mark collected", key=f"collect_{oid}", width="stretch"):
                    res, msg = core.collect_order(oid, user["user_id"], code)
                    if res:
                        st.session_state["_flash"] = ("success", msg)
                        st.rerun()
                    st.error(msg)
                if c2.button("Cancel", key=f"vendor_cancel_{oid}", width="stretch"):
                    res, msg = core.cancel_order(oid, user["user_id"], user["role"])
                    if res:
                        st.session_state["_flash"] = ("success", msg)
                        st.rerun()
                    st.error(msg)
        hist = all_orders[all_orders["status"].isin(["Collected", "Cancelled"])] if len(all_orders) else all_orders
        if len(hist):
            st.subheader("History")
            st.dataframe(hist, hide_index=True, width="stretch")


{"Home": home, "Order Food": order_page, "Wallet": wallet_page,
 "Refer a Friend": referral_page, "Vendor Dashboard": vendor_page}[page]()
