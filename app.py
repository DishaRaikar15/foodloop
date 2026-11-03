"""FoodLoop - turn canteen surplus into savings.  Run:  streamlit run app.py"""
import json
from datetime import datetime

import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="FoodLoop", page_icon="♻️", layout="wide")
ui.inject_css()

core.seed_if_empty()

# ---------------- Session Persistence ----------------
SESSION_FILE = core.DATA / ".active_session.json"


def save_session(user_dict: dict):
    """Persist active login session to disk and query parameters."""
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"user_id": int(user_dict["user_id"])}, f)
        st.query_params["uid"] = str(user_dict["user_id"])
    except Exception:
        pass


def get_saved_session():
    """Retrieve persisted session from query params or disk cache."""
    user_id = None
    if "uid" in st.query_params:
        try:
            user_id = int(st.query_params["uid"])
        except (ValueError, TypeError):
            pass
    if user_id is None and SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                user_id = int(data.get("user_id"))
        except Exception:
            pass
    if user_id is not None:
        users = core.read("users")
        matches = users[users["user_id"] == user_id]
        if not matches.empty:
            return matches.iloc[0].to_dict()
    return None


def clear_session():
    """Wipe session cache, state, and query parameters on logout."""
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
    except Exception:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("nav_page", None)
    st.session_state.pop("_redirect_page", None)
    st.query_params.clear()


# Restore session if not already in session_state
if st.session_state.get("user") is None:
    saved = get_saved_session()
    if saved:
        st.session_state["user"] = saved

user = st.session_state.get("user")


# ---------------- Unauthenticated View: Dedicated Login / Register ----------------
if user is None:
    with st.sidebar:
        st.title("♻️ FoodLoop")
        st.write("Welcome! Please log in or register to access student deals or vendor canteen tools.")
        st.caption("Campus food waste reduction platform.")

    ui.navbar("FoodLoop")
    ui.hero("Welcome to", "FoodLoop", "Turn campus canteen surplus into delicious, affordable meals.")

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="fl-card" style="padding: 2rem;">', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["🔑 Log In", "📝 Create Account"])

        with tab_login:
            with st.form("main_login_form"):
                e = st.text_input("Email", placeholder="student@foodloop.com", key="auth_login_email")
                p = st.text_input("Password", type="password", key="auth_login_password")
                submit_login = st.form_submit_button("Log In", width="stretch")
                if submit_login:
                    u = core.login(e, p)
                    if u:
                        save_session(u)
                        st.session_state["user"] = u
                        st.session_state["_redirect_page"] = "Explore Deals" if u["role"] == "student" else "Overview"
                        st.rerun()
                    st.error("Wrong email or password.")

            st.markdown(
                """
                <div style="background: #FFF4EA; border-radius: 12px; padding: 12px 14px; margin-top: 14px; font-size: 0.85rem; color: #4B5563; border: 1px solid #FFE8D6;">
                    <b>Demo Credentials:</b><br/>
                    🎓 Student: <code>student@foodloop.com</code> / <code>student123</code><br/>
                    🏪 Canteen Vendor: <code>canteen@foodloop.com</code> / <code>vendor123</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab_register:
            with st.form("main_register_form"):
                n = st.text_input("Full Name", placeholder="Alex Smith", key="auth_reg_name")
                e2 = st.text_input("Email", placeholder="alex@campus.edu", key="auth_reg_email")
                p2 = st.text_input("Password", type="password", key="auth_reg_password")
                role = st.selectbox("I am a", ["student", "vendor"], key="auth_reg_role")
                code = st.text_input("Referral code (optional)", key="auth_reg_code")
                submit_reg = st.form_submit_button("Create Account", width="stretch")
                if submit_reg:
                    row, msg = core.register(n, e2, p2, role, code)
                    if row:
                        st.success(msg + " You can now switch to the Log In tab.")
                    else:
                        st.error(msg)

        st.markdown('</div>', unsafe_allow_html=True)

    ui.footer()
    st.stop()

else:
    # ---------------- Authenticated User Portals ----------------
    # Sidebar Account Controls
    with st.sidebar:
        st.title("♻️ FoodLoop")
        st.write(f"Logged in as **{user['name']}**")
        if user["role"] == "student":
            st.caption("Role: Student 🎓")
            bal = core.balance(user["user_id"])
            st.metric("Your Points", f"⭐ {bal}")
        else:
            st.caption("Role: Canteen Vendor 🏪")
            with st.expander("Demo Controls"):
                if st.button("Reset demo listings", width="stretch"):
                    core.reset_demo_listings()
                    st.rerun()

        if st.button("Logout", width="stretch"):
            clear_session()
            st.rerun()

    # Top Brand & Role-Based Navigation
    ui.navbar("FoodLoop")

    if user["role"] == "student":
        pages = ["Explore Deals", "Order Food", "Wallet", "Refer a Friend"]
    else:
        pages = ["Overview", "Add Surplus", "Orders & Pickup", "Sales & Forecast"]

    if "_redirect_page" in st.session_state:
        st.session_state["nav_page"] = st.session_state.pop("_redirect_page")

    if st.session_state.get("nav_page") not in pages:
        st.session_state["nav_page"] = pages[0]

    page = st.radio("Navigation", pages, horizontal=True, label_visibility="collapsed", key="nav_page")

    # ==============================================================================
    # STUDENT PAGES
    # ==============================================================================
    def student_explore():
        ui.hero("Good food shouldn't go to", "waste", f"Hello {user['name']}! Save money and reduce campus canteen food waste.")

        sc1, sc2 = st.columns([5, 1])
        with sc1:
            search_query = st.text_input("Search deals", placeholder="Search by food name (e.g., thali, roll, samosa)...", label_visibility="collapsed")
        with sc2:
            st.button("Find deals", width="stretch")

        imp = core.impact()
        ui.impact_pill(imp["portions"], imp["co2"])

        st.subheader("Explore categories")
        selected_cat = ui.category_tiles()

        st.subheader("Live surplus deals")
        items = core.live_items()
        if items.empty:
            st.info("No surplus right now. Check back soon!")
            ui.promo_banner("Refer a friend, you both get 20 points 🎁", "Points are automatically credited after their first collected order.")
            ui.footer()
            return

        # Filter items by search text and by selected category
        filtered = items.copy()
        if search_query and search_query.strip():
            filtered = filtered[filtered["name"].str.contains(search_query.strip(), case=False, na=False)]

        if selected_cat == "Meals":
            filtered = filtered[filtered["name"].str.contains(r"thali|meal", case=False, na=False, regex=True)]
        elif selected_cat == "Rolls":
            filtered = filtered[filtered["name"].str.contains(r"roll|wrap", case=False, na=False, regex=True)]
        elif selected_cat == "Snacks":
            filtered = filtered[filtered["name"].str.contains(r"samosa|snack", case=False, na=False, regex=True)]
        elif selected_cat == "South Indian":
            filtered = filtered[filtered["name"].str.contains(r"dosa|idli|vada|south", case=False, na=False, regex=True)]

        if filtered.empty:
            st.info(f"No items match '{selected_cat}' or your search query. Try another category!")
        else:
            # 3-column grid of deal cards with orange Order Now button
            cols = st.columns(3)
            for i, (_, row) in enumerate(filtered.iterrows()):
                col = cols[i % 3]
                with col:
                    ui.deal_card(row)
                    item_id = int(row["item_id"])
                    if st.button("Order Now", key=f"home_order_{item_id}", width="stretch"):
                        st.session_state["selected_item_id"] = item_id
                        st.session_state["_redirect_page"] = "Order Food"
                        st.rerun()

        ui.promo_banner("Refer a friend, you both get 20 points 🎁", "Points are automatically credited after their first collected order.")

        with st.expander("How our dynamic discount works"):
            st.table(pd.DataFrame({
                "Time remaining": ["> 3 hours", "2 - 3 hours", "1 - 2 hours", "30 min - 1 hour", "< 30 minutes"],
                "Discount": ["0%", "15%", "25%", "40%", "50%"]
            }))

        ui.footer()

    def student_order():
        ui.hero("Order surplus food", "Fast", "Rescue fresh meals before time runs out and earn rewards.")
        items = core.live_items()
        if items.empty:
            st.info("Nothing available right now. Check back soon!")
            ui.footer()
            return

        item_ids = items["item_id"].tolist()
        preselected = st.session_state.pop("selected_item_id", None)
        default_idx = item_ids.index(preselected) if preselected in item_ids else 0

        st.markdown('<div class="fl-card" style="padding: 1.5rem;">', unsafe_allow_html=True)
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

        ui.footer()

    def student_wallet():
        flash = st.session_state.pop("_flash", None)
        if flash:
            getattr(st, flash[0])(flash[1])
        w = core.wallet_summary(user["user_id"])
        pending = core.pending_points(user["user_id"])

        ui.hero("FoodLoop Wallet", "Balance", "Track your eco-points, transactions, and active pickup passes.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Available points", w["balance"])
        m2.metric("Total earned", w["earned"])
        m3.metric("Total redeemed", w["redeemed"])
        m4.metric("Pending points", pending)

        st.subheader("Transaction history")
        st.dataframe(w["history"], hide_index=True, width="stretch")

        st.subheader("My orders")
        orders = core.student_orders(user["user_id"])
        if orders.empty:
            st.info("No orders yet.")
            ui.footer()
            return

        for _, row in orders.iterrows():
            oid = int(row["order_id"])
            status = str(row["status"])
            badge_html = ui.status_badge(status)
            st.markdown(
                f"""
                <div class="fl-card" style="padding: 1.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span style="font-size: 1.15rem; font-weight: 800; color: #1F1B2D;">{row['item_name']}</span>
                            <span style="color: #6B7280; font-weight: 600; margin-left: 8px;">&times; {int(row['qty'])}</span>
                        </div>
                        <div>{badge_html}</div>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #4B5563; font-size: 0.95rem;">
                        <span>Order #{oid} &bull; {str(row['created_at'])[:16]}</span>
                        <span>Total Paid: <b style="color: #F26B1D;">₹{int(row['total_paid'])}</b></span>
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

        ui.footer()

    def student_referral():
        ui.hero("Refer a friend", "Together", "Share the surplus movement and earn bonus points.")
        st.markdown('<div class="fl-card" style="padding: 1.5rem;">', unsafe_allow_html=True)
        st.write(f"Share your referral code. When a new student registers with it and completes their first "
                 f"purchase, **both of you get {core.REFERRAL_BONUS} points**.")
        st.code(user["ref_code"])
        st.markdown('</div>', unsafe_allow_html=True)
        ui.footer()

    # ==============================================================================
    # VENDOR PAGES
    # ==============================================================================
    def vendor_overview():
        flash = st.session_state.pop("_flash", None)
        if flash:
            getattr(st, flash[0])(flash[1])

        ui.hero("Canteen Dashboard", "Overview", f"Welcome back, {user['name']}.")

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

        # 4 metric tiles on top
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Revenue from surplus", f"₹{revenue}")
        m2.metric("Orders collected", orders_collected)
        m3.metric("Active listings", active_listings)
        m4.metric("Portions saved", portions_saved)

        if len(live_mine):
            st.subheader("Your active listings")
            st.dataframe(live_mine[["name", "mrp", "quantity", "minutes_left", "discount_%", "price_now"]],
                         hide_index=True, width="stretch")

        f = core.forecast()
        if not f.empty:
            st.subheader("Quick waste forecast")
            for msg in f["advice"].head(2):
                st.info("💡 " + msg)

        ui.footer()

    def vendor_add_surplus():
        ui.hero("Add Surplus", "Listings", "Publish fresh unsold food portions with automatic dynamic discounts.")

        with st.form("add"):
            name = st.text_input("Item name", placeholder="e.g. Veg Biryani, Paneer Roll")
            mrp = st.number_input("MRP (₹)", 1, 2000, 80)
            qty = st.number_input("Portions available", 1, 500, 10)
            hrs = st.slider("Valid for (hours)", 0.5, 6.0, 2.0, 0.5)
            if st.form_submit_button("Publish Surplus Listing", width="stretch"):
                row, msg = core.add_item(user["user_id"], name, mrp, qty, hrs)
                if row:
                    st.success(msg)
                else:
                    st.error(msg)

        live = core.live_items()
        mine = core.vendor_items(user["user_id"])
        live_mine = live[live["item_id"].isin(mine["item_id"])] if len(live) and len(mine) else live.iloc[0:0]
        if len(live_mine):
            st.subheader("Current active listings")
            st.dataframe(live_mine[["name", "mrp", "quantity", "minutes_left", "discount_%", "price_now"]],
                         hide_index=True, width="stretch")

        ui.footer()

    def vendor_orders_page():
        flash = st.session_state.pop("_flash", None)
        if flash:
            getattr(st, flash[0])(flash[1])

        ui.hero("Canteen Orders", "Verification", "Verify student pickup codes and mark orders as collected.")

        all_orders = core.vendor_orders(user["user_id"])
        pending = all_orders[all_orders["status"] == "Pending"] if len(all_orders) else all_orders

        st.subheader("Pending orders awaiting pickup")
        if pending.empty:
            st.info("No pending orders right now.")
        else:
            for _, row in pending.iterrows():
                oid = int(row["order_id"])
                st.markdown(
                    f"""
                    <div class="fl-card" style="padding: 1.25rem;">
                        <div style="font-size: 1.15rem; font-weight: 700; color: #1F1B2D;">{row['item_name']} &times; {int(row['qty'])} &mdash; ₹{int(row['total_paid'])}</div>
                        <div style="font-size: 0.85rem; color: #6B7280; margin-top: 2px;">Order #{oid} &bull; Ordered at {str(row['created_at'])[:16]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                code = st.text_input("Enter 6-digit pickup code", key=f"collect_code_{oid}")
                c1, c2 = st.columns(2)
                if c1.button("Mark collected", key=f"collect_{oid}", width="stretch"):
                    res, msg = core.collect_order(oid, user["user_id"], code)
                    if res:
                        st.session_state["_flash"] = ("success", msg)
                        st.rerun()
                    st.error(msg)
                if c2.button("Cancel order", key=f"vendor_cancel_{oid}", width="stretch"):
                    res, msg = core.cancel_order(oid, user["user_id"], user["role"])
                    if res:
                        st.session_state["_flash"] = ("success", msg)
                        st.rerun()
                    st.error(msg)

        hist = all_orders[all_orders["status"].isin(["Collected", "Cancelled"])] if len(all_orders) else all_orders
        if len(hist):
            st.subheader("Order history")
            st.dataframe(hist, hide_index=True, width="stretch")

        ui.footer()

    def vendor_sales_forecast():
        ui.hero("Sales & Forecast", "Analytics", "Analyze surplus sales and reduce waste with historical forecasts.")

        all_orders = core.vendor_orders(user["user_id"])
        collected = all_orders[all_orders["status"] == "Collected"] if len(all_orders) else all_orders

        if collected.empty:
            st.info("No collected orders yet to analyze.")
        else:
            st.subheader("Sales per item (portions sold)")
            sales_by_item = collected.groupby("item_name")["qty"].sum()
            st.bar_chart(sales_by_item, color="#F26B1D")

            st.subheader("Collected orders list")
            st.dataframe(collected, hide_index=True, width="stretch")

        st.subheader("Waste reduction forecast")
        f = core.forecast()
        if f.empty:
            st.info("Not enough preparation history yet.")
        else:
            for msg in f["advice"]:
                st.info("💡 " + msg)
            st.dataframe(f, hide_index=True, width="stretch")

        ui.footer()

    # ---------------- Routing ----------------
    routes = {
        # Student routes
        "Explore Deals": student_explore,
        "Order Food": student_order,
        "Wallet": student_wallet,
        "Refer a Friend": student_referral,
        # Vendor routes
        "Overview": vendor_overview,
        "Add Surplus": vendor_add_surplus,
        "Orders & Pickup": vendor_orders_page,
        "Sales & Forecast": vendor_sales_forecast,
    }

    routes[page]()
