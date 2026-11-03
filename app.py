"""FoodLoop - turn canteen surplus into savings.  Run:  streamlit run app.py"""
import json
from datetime import datetime

import pandas as pd
import streamlit as st

import core
import ui

st.set_page_config(page_title="FoodLoop", page_icon="♻️", layout="wide")
ui.inject_css()

# Branded order-success modal: blurred backdrop and elevated confirmation card.
st.markdown(
    """
    <style>
    div[data-testid="stDialog"] {
        background: rgba(25, 20, 35, 0.48) !important;
        -webkit-backdrop-filter: blur(10px) saturate(115%) !important;
        backdrop-filter: blur(10px) saturate(115%) !important;
    }
    div[data-testid="stDialog"] [role="dialog"] {
        background: linear-gradient(155deg, #FFFFFF 0%, #FFF5EC 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 28px !important;
        box-shadow: 0 28px 90px rgba(20, 15, 30, 0.30), 0 8px 28px rgba(242, 107, 29, 0.12) !important;
        overflow: hidden !important;
    }
    div[data-testid="stDialog"] [role="dialog"] > div {
        padding: 1.6rem 1.8rem 1.8rem !important;
    }
    .fl-success-modal { text-align: center; padding: 0.4rem 0.25rem 1rem; }
    .fl-success-icon-wrap { position: relative; width: 104px; height: 104px; margin: 0.2rem auto 1.15rem; display: grid; place-items: center; border-radius: 50%; background: radial-gradient(circle, #FFF0E3 0%, #FFE1C8 68%, rgba(255,225,200,0) 70%); animation: fl-pop-in .55s cubic-bezier(.2, .9, .25, 1.3) both; }
    .fl-success-icon { width: 68px; height: 68px; display: grid; place-items: center; border-radius: 50%; background: linear-gradient(145deg, #FF8A3D, #F26B1D); color: white; font-size: 2.65rem; font-weight: 800; line-height: 1; box-shadow: 0 10px 24px rgba(242,107,29,.32), inset 0 2px 3px rgba(255,255,255,.35); }
    .fl-success-eyebrow { color: #F26B1D; font-size: .70rem; font-weight: 800; letter-spacing: 2px; margin-bottom: .55rem; }
    .fl-success-modal h2 { color: #1F1B2D; font-size: 1.8rem; line-height: 1.2; font-weight: 800; margin: 0 0 .65rem; letter-spacing: -.7px; }
    .fl-success-modal p { color: #6B7280; font-size: .98rem; line-height: 1.65; margin: 0 auto 1.15rem; max-width: 390px; }
    .fl-success-modal p b { color: #1F1B2D; }
    .fl-success-tag { display: inline-block; background: #FFF0E3; color: #B94D0D; border: 1px solid #FFD9BD; border-radius: 999px; padding: .55rem .95rem; font-size: .82rem; font-weight: 700; }
    .fl-success-spark { position: absolute; color: #F26B1D; font-size: 1.3rem; animation: fl-sparkle 1.8s ease-in-out infinite; }
    .fl-spark-one { top: 8px; right: 5px; }
    .fl-spark-two { bottom: 9px; left: 3px; animation-delay: .5s; }
    @keyframes fl-pop-in { from { opacity: 0; transform: scale(.72) translateY(12px); } to { opacity: 1; transform: scale(1) translateY(0); } }
    @keyframes fl-sparkle { 0%, 100% { opacity: .35; transform: scale(.8) rotate(0deg); } 50% { opacity: 1; transform: scale(1.2) rotate(18deg); } }
    @media (prefers-reduced-motion: reduce) { .fl-success-icon-wrap, .fl-success-spark { animation: none !important; } }
    </style>
    """,
    unsafe_allow_html=True,
)


core.seed_if_empty()
core.ensure_demo_listings()

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
        return core.get_user(user_id)
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


@st.dialog(" ", width="small")
def show_cart_order_success_dialog():
    """Show the same centered success confirmation for cart checkout."""
    st.markdown(
        """
        <div class="fl-success-modal">
            <div class="fl-success-icon-wrap">
                <div class="fl-success-icon">✓</div>
                <span class="fl-success-spark fl-spark-one">✦</span>
                <span class="fl-success-spark fl-spark-two">✧</span>
            </div>
            <div class="fl-success-eyebrow">FOODLOOP CONFIRMATION</div>
            <h2>Your cart order is in!</h2>
            <p>Your selected food items have been reserved successfully. Your individual pickup verification codes are ready on this Cart page.</p>
            <div class="fl-success-tag">♻️ &nbsp; Good food saved from waste</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("View pickup codes", type="primary", width="stretch", key="close_cart_order_success"):
        st.session_state["_show_cart_order_success"] = False
        st.rerun()


@st.dialog(" ", width="small")
def show_order_success_dialog():
    """Display a centered, branded order confirmation modal."""
    st.markdown(
        """
        <div class="fl-success-modal">
            <div class="fl-success-icon-wrap">
                <div class="fl-success-icon">✓</div>
                <span class="fl-success-spark fl-spark-one">✦</span>
                <span class="fl-success-spark fl-spark-two">✧</span>
            </div>
            <div class="fl-success-eyebrow">FOODLOOP CONFIRMATION</div>
            <h2>Your order is in!</h2>
            <p>Your food has been reserved successfully. Head to <b>My Orders</b> to check its status and pickup details.</p>
            <div class="fl-success-tag">♻️ &nbsp; Good food saved from waste</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Continue browsing", type="primary", width="stretch", key="close_order_success"):
        st.session_state["_show_order_success"] = False
        st.rerun()


# Restore session if not already in session_state
if st.session_state.get("user") is None:
    saved = get_saved_session()
    if saved:
        st.session_state["user"] = saved

user = st.session_state.get("user")


# ---------------- Unauthenticated View: Split-panel Login / Register ----------------
if user is None:
    # Keep the existing FoodLoop illustration panel; place the complete auth UI
    # inside a matching white panel to its right.
    st.markdown(
        """
        <style>
        .block-container:has(.fl-auth-left) { max-width:1500px !important; padding-top:1.25rem !important; padding-bottom:1.5rem !important; }
        /* Stretch both Streamlit columns and give their panels identical desktop dimensions. */
        .block-container:has(.fl-auth-left) div[data-testid="stHorizontalBlock"] { align-items:stretch !important; }
        .block-container:has(.fl-auth-left) div[data-testid="column"] { display:flex !important; align-items:stretch !important; }
        .fl-auth-shell { width:100%; height:840px !important; min-height:840px !important; border-radius:28px; overflow:hidden; box-shadow:0 18px 55px rgba(51,35,22,.12); border:1px solid rgba(242,107,29,.10); box-sizing:border-box; }
        .fl-auth-left { padding:2.6rem 2.2rem; color:#251b2c; background:radial-gradient(circle at 18% 18%,rgba(255,255,255,.22) 0 7px,transparent 8px),radial-gradient(circle at 82% 28%,rgba(255,255,255,.18) 0 10px,transparent 11px),linear-gradient(145deg,#FF9F0A 0%,#F36B18 100%); display:flex; flex-direction:column; justify-content:space-between; text-align:center; }
        .fl-auth-brand { color:#241b2d; font-size:1.5rem; font-weight:850; letter-spacing:-.6px; text-align:left; }
        .fl-auth-art { font-size:6.8rem; line-height:1.25; margin:3.2rem auto 2rem; filter:drop-shadow(0 12px 12px rgba(87,42,0,.16)); }
        .fl-auth-left h2 { color:#241b2d; font-size:1.8rem; font-weight:850; margin:.3rem 0 .7rem; }
        .fl-auth-left p { color:rgba(36,27,45,.83); font-size:1rem; line-height:1.6; max-width:370px; margin:0 auto; }
        .fl-auth-dots { color:rgba(255,255,255,.85); letter-spacing:8px; font-size:1.25rem; margin-top:2rem; }
        .st-key-fl_auth_right_panel { width:100%; height:840px !important; min-height:840px !important; box-sizing:border-box; display:flex; flex-direction:column; justify-content:flex-start !important; align-self:stretch !important; background:#fff !important; border:1px solid rgba(242,107,29,.10) !important; border-radius:28px !important; padding:2.1rem clamp(1.2rem,3vw,3rem) !important; box-shadow:0 18px 55px rgba(51,35,22,.12) !important; }
        .fl-auth-welcome { text-align:center; padding:.35rem 0 1.1rem; }
        .fl-auth-mark { width:76px; height:76px; margin:0 auto 1rem; border-radius:24px; display:grid; place-items:center; background:#FFF2E6; color:#F36B18; font-size:2.7rem; }
        .fl-auth-welcome h2 { color:#211b2c; font-size:1.85rem; font-weight:800; margin:0 0 .45rem; }
        .fl-auth-welcome p { color:#77717d; margin:0; font-size:.95rem; }
        .fl-auth-foot { color:#8b8490; font-size:.82rem; text-align:center; margin-top:1.2rem; }
        .st-key-fl_auth_right_panel div[data-testid="stForm"] { border:0 !important; padding:0 !important; }
        .st-key-fl_auth_right_panel div[data-testid="stTextInput"] input { border-radius:11px !important; min-height:3rem !important; }
        .st-key-fl_auth_right_panel div[data-testid="stFormSubmitButton"] button { border-radius:10px !important; min-height:3.1rem !important; font-weight:750 !important; }
        @media (max-width:850px) {
          .block-container:has(.fl-auth-left) div[data-testid="stHorizontalBlock"] { flex-direction:column !important; }
          .fl-auth-shell { height:auto !important; min-height:390px !important; }
          .fl-auth-left { padding:1.6rem; }
          .fl-auth-art { font-size:4rem; margin:1rem auto; }
          .st-key-fl_auth_right_panel { height:auto !important; min-height:480px !important; padding:1.5rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1], gap="medium")
    with left:
        st.markdown(
            """
            <div class="fl-auth-shell fl-auth-left">
              <div class="fl-auth-brand">🟠 FoodLoop</div>
              <div>
                <div class="fl-auth-art">🍟 🍔 🥗</div>
                <h2>Good food deserves another chance.</h2>
                <p>Discover fresh surplus meals from campus canteens, save money and help reduce food waste.</p>
                <div class="fl-auth-dots">● ● ●</div>
              </div>
              <p style="font-size:.82rem;font-weight:650;">Rescue food · Save money · Make an impact</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        with st.container(key="fl_auth_right_panel"):
            st.markdown(
                """
                <div class="fl-auth-welcome">
                  <div class="fl-auth-mark">♻️</div>
                  <h2>Welcome to FoodLoop</h2>
                  <p>Log in to find deals and make every meal count.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            tab_login, tab_register = st.tabs(["🔑  Log In", "📝  Create Account"])

            with tab_login:
                # Step 1: choose an account type. Keep the credentials hidden
                # until the user makes a selection.
                if "auth_login_step" not in st.session_state:
                    st.session_state["auth_login_step"] = "choose"
                if "auth_selected_role" not in st.session_state:
                    st.session_state["auth_selected_role"] = None

                if st.session_state["auth_login_step"] == "choose":
                    st.markdown(
                        "<div style='text-align:center;margin:.6rem 0 1.2rem;'>"
                        "<h3 style='margin-bottom:.35rem;color:#211b2c;'>How would you like to log in?</h3>"
                        "<p style='color:#77717d;margin:0;'>Choose your account type to continue.</p></div>",
                        unsafe_allow_html=True,
                    )
                    role_col1, role_col2 = st.columns(2, gap="medium")
                    with role_col1:
                        st.markdown(
                            "<div style='text-align:center;background:#FFF7F0;border:1px solid #FFE1CC;"
                            "border-radius:18px;padding:1.1rem .6rem .7rem;'>"
                            "<div style='font-size:2.6rem;'>🎒</div>"
                            "<div style='font-size:1.05rem;font-weight:800;color:#211b2c;'>Student</div>"
                            "<div style='font-size:.78rem;color:#77717d;'>Discover deals and save meals</div></div>",
                            unsafe_allow_html=True,
                        )
                        if st.button("Continue as Student", key="choose_student_login", width="stretch", type="primary"):
                            st.session_state["auth_selected_role"] = "student"
                            st.session_state["auth_login_step"] = "credentials"
                            st.rerun()
                    with role_col2:
                        st.markdown(
                            "<div style='text-align:center;background:#FFF7F0;border:1px solid #FFE1CC;"
                            "border-radius:18px;padding:1.1rem .6rem .7rem;'>"
                            "<div style='font-size:2.6rem;'>🍽️</div>"
                            "<div style='font-size:1.05rem;font-weight:800;color:#211b2c;'>Canteen / Vendor</div>"
                            "<div style='font-size:.78rem;color:#77717d;'>List food and manage orders</div></div>",
                            unsafe_allow_html=True,
                        )
                        if st.button("Continue as Vendor", key="choose_vendor_login", width="stretch", type="secondary"):
                            st.session_state["auth_selected_role"] = "vendor"
                            st.session_state["auth_login_step"] = "credentials"
                            st.rerun()
                else:
                    expected_role = st.session_state["auth_selected_role"]
                    role_label = "Student" if expected_role == "student" else "Canteen / Vendor"
                    st.markdown(
                        f"<div style='text-align:center;margin:.35rem 0 1rem;'>"
                        f"<div style='font-size:2.3rem;'>{'🎒' if expected_role == 'student' else '🍽️'}</div>"
                        f"<h3 style='margin:.2rem 0;color:#211b2c;'>{role_label} Login</h3>"
                        "<p style='color:#77717d;margin:0;'>Enter your account details to continue.</p></div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("← Change account type", key="back_to_account_type", type="secondary"):
                        st.session_state["auth_login_step"] = "choose"
                        st.session_state["auth_selected_role"] = None
                        st.rerun()

                    with st.form("main_login_form"):
                        e = st.text_input("Email address", placeholder="Enter your email", key="auth_login_email")
                        p = st.text_input("Password", type="password", placeholder="Enter your password", key="auth_login_password")
                        submit_login = st.form_submit_button("Log In", width="stretch", type="primary")
                        if submit_login:
                            u = core.login(e, p)
                            if not u:
                                st.error("Incorrect email or password. Please try again.")
                            elif str(u.get("role", "")).lower() != expected_role:
                                st.error(f"This account is not registered as a {role_label.lower()}. Select the correct account type and try again.")
                            else:
                                save_session(u)
                                st.session_state["user"] = u
                                st.session_state["_redirect_page"] = "Explore Deals" if expected_role == "student" else "Overview"
                                st.rerun()

            with tab_register:
                st.info("New accounts are currently available for students only.")
                with st.form("main_register_form"):
                    n = st.text_input("Full name", placeholder="Enter your full name", key="auth_reg_name")
                    e2 = st.text_input("Email address", placeholder="name@campus.edu", key="auth_reg_email")
                    p2 = st.text_input("Password", type="password", placeholder="Create a password", key="auth_reg_password")
                    code = st.text_input("Referral code (optional)", key="auth_reg_code")
                    submit_reg = st.form_submit_button("Create Student Account", width="stretch", type="primary")
                    if submit_reg:
                        row, msg = core.register(n, e2, p2, "student", code)
                        if row:
                            st.success(msg + " You can now log in as a student.")
                        else:
                            st.error(msg)

            st.markdown('<div class="fl-auth-foot">Making every meal count ♻️</div>', unsafe_allow_html=True)

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
        pages = ["Explore Deals", "Cart", "My Orders", "Wallet", "Reviews", "Refer a Friend", "Logout"]
    else:
        pages = ["Overview", "Add Surplus", "Orders & Pickup", "Sales & Forecast", "Logout"]

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

        st.markdown("### Find your next deal")
        search_query = st.text_input("Search food", placeholder="Search by food name...", key="food_search")
        with st.expander("⚙️ Filters & preferences", expanded=False):
            f1, f2, f3 = st.columns(3)
            with f1:
                max_price = st.slider("Maximum price per portion (₹)", 20, 300, 300, 10)
            with f2:
                min_discount = st.selectbox("Minimum discount", ["Any", "15%", "25%", "40%", "50%"])
            with f3:
                expiry_filter = st.selectbox("Time remaining", ["Any", "Under 1 hour", "1–2 hours", "Over 2 hours"])
            dietary_filter = st.radio("Food preference", ["All", "Vegetarian", "Non-vegetarian"], horizontal=True, key="dietary_filter")
            st.caption("Choose a category")
            selected_cat = ui.category_tiles()

        imp = core.impact()
        ui.impact_pill(imp["portions"], imp["co2"])

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

        # Use explicit menu categories instead of fragile food-name keyword filters.
        filtered["category"] = filtered["name"].apply(core.category_for_item)
        # Dietary classification is name-based until vendors provide an explicit field.
        non_veg_terms = ("chicken", "egg", "fish", "prawn", "mutton", "meat", "keema", "omelette", "omelet", "non veg", "non-veg")
        filtered["diet_type"] = filtered["name"].astype(str).str.lower().apply(
            lambda name: "Non-vegetarian" if any(term in name for term in non_veg_terms) else "Vegetarian"
        )
        if dietary_filter != "All":
            filtered = filtered[filtered["diet_type"] == dietary_filter]
        if selected_cat != "All":
            filtered = filtered[filtered["category"] == selected_cat]
        filtered = filtered[filtered["price_now"].astype(float) <= max_price]
        if min_discount != "Any":
            filtered = filtered[filtered["discount_%"].astype(int) >= int(min_discount.replace("%", ""))]
        if expiry_filter == "Under 1 hour":
            filtered = filtered[filtered["minutes_left"] <= 60]
        elif expiry_filter == "1–2 hours":
            filtered = filtered[(filtered["minutes_left"] > 60) & (filtered["minutes_left"] <= 120)]
        elif expiry_filter == "Over 2 hours":
            filtered = filtered[filtered["minutes_left"] > 120]

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
                    avg_rating, review_count = core.item_rating_summary(item_id)
                    st.caption(f"⭐ {avg_rating}/5 ({review_count} reviews)" if review_count else "New listing · Be the first to review")
                    qcol, bcol = st.columns([1, 2])
                    qty_add = qcol.number_input("Qty", min_value=1, max_value=int(row["quantity"]), value=1, key=f"add_qty_{item_id}")
                    if bcol.button("Add to cart", key=f"add_cart_{item_id}", width="stretch"):
                        cart = st.session_state.setdefault("foodloop_cart", {})
                        cart[item_id] = min(int(row["quantity"]), int(cart.get(item_id, 0)) + int(qty_add))
                        st.toast(f"{row['name']} added to cart", icon="🛒")

        ui.promo_banner("Refer a friend, you both get 20 points 🎁", "Points are automatically credited after their first collected order.")

        with st.expander("How our dynamic discount works"):
            st.table(pd.DataFrame({
                "Time remaining": ["> 3 hours", "2 - 3 hours", "1 - 2 hours", "30 min - 1 hour", "< 30 minutes"],
                "Discount": ["0%", "15%", "25%", "40%", "50%"]
            }))

        ui.footer()

    def student_cart():
        ui.hero("Your Cart", "Checkout", "Review your rescued food before placing one combined order.")
        cart = st.session_state.setdefault("foodloop_cart", {})
        recent_cart_orders = st.session_state.get("_cart_pickups", [])
        if recent_cart_orders:
            if st.session_state.get("_show_cart_order_success", False):
                show_cart_order_success_dialog()
            st.success("Your cart checkout was placed. Show the relevant pickup code to the canteen worker for each item.")
            st.subheader("Your pickup verification codes")
            for saved_order in recent_cart_orders:
                ui.pickup_card(saved_order)
            if st.button("Hide pickup details", key="hide_cart_pickups"):
                st.session_state.pop("_cart_pickups", None)
                st.session_state.pop("_show_cart_order_success", None)
                st.rerun()
        live = core.live_items()
        if not cart:
            st.info("Your cart is empty. Add food from Explore Deals.")
        else:
            total = 0
            for item_id in list(cart):
                match = live[live["item_id"].astype(str) == str(item_id)]
                if match.empty:
                    st.warning(f"Item #{item_id} is no longer available and was removed from your cart.")
                    cart.pop(item_id, None)
                    continue
                row = match.iloc[0]
                image_col, details_col, qty_col, remove_col = st.columns([0.85, 3.4, 1.35, 1.0], vertical_alignment="center")
                with image_col:
                    st.image(ui.food_image_url(row["name"]), width=104)
                with details_col:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"₹{int(row['price_now'])} each · {int(row['quantity'])} available")
                new_qty = qty_col.number_input("Qty", 1, int(row["quantity"]), min(int(cart[item_id]), int(row["quantity"])), key=f"cart_qty_{item_id}")
                cart[item_id] = int(new_qty)
                if remove_col.button("Remove", key=f"cart_remove_{item_id}"):
                    cart.pop(item_id, None)
                    st.rerun()
                unit = int(row["group_price"] if new_qty >= core.GROUP_MIN_QTY else row["price_now"])
                total += unit * int(new_qty)
            st.divider()
            st.subheader(f"Items subtotal: ₹{total}")
            st.caption("Group pricing is automatically applied to a line with 5 or more portions.")
            coupon = st.text_input("Coupon code", placeholder="Try SAVE10, FOODLOOP20 or RESCUE15", key="cart_coupon").strip().upper()
            discount, coupon_msg = core.coupon_discount(coupon, total) if coupon else (0, "")
            if coupon:
                if discount:
                    st.success(f"{coupon_msg} You save ₹{discount}.")
                else:
                    st.error(coupon_msg)
            wallet_cap = core.max_redeemable(user["user_id"], max(0, total - discount))
            points = st.slider("Redeem wallet points (₹1 = 1 point)", 0, wallet_cap, 0, key="cart_points") if wallet_cap else 0
            st.markdown(f"### Payable: ₹{max(0, total - discount - points)}")
            if st.button("Place combined order", type="primary", width="stretch", disabled=not cart):
                results, message = core.place_cart_order(user["user_id"], cart.copy(), points, coupon)
                if results:
                    st.session_state["foodloop_cart"] = {}
                    st.session_state["_cart_pickups"] = [
                        {**order, "pickup_code": str(order.get("pickup_code", "")).zfill(6)}
                        for order in results
                    ]
                    st.session_state["_show_cart_order_success"] = True
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)
        st.subheader("Available coupons")
        for code, offer in core.COUPONS.items():
            st.markdown(f"**{code}** — {offer['description']}")
        st.divider()
        st.subheader("Find food within your budget")
        budget = st.number_input("Your budget (₹)", min_value=20, max_value=2000, value=100, step=10, key="budget_suggest")
        available = core.live_items().sort_values("price_now")
        affordable = available[available["price_now"] <= budget]
        if affordable.empty:
            st.info("No single portions currently fit this budget. Try increasing it.")
        else:
            st.write("**Affordable individual items**")
            st.dataframe(affordable[["name", "price_now", "quantity", "minutes_left"]].head(8).rename(columns={"name":"Food", "price_now":"Price (₹)", "quantity":"Available", "minutes_left":"Minutes left"}), hide_index=True, width="stretch")
            st.write("**Suggested combination**")
            remaining = int(budget)
            picks = []
            for _, item in affordable.iterrows():
                count = min(int(item["quantity"]), remaining // max(1, int(item["price_now"])))
                if count > 0:
                    picks.append((int(item["item_id"]), str(item["name"]), count, int(item["price_now"])))
                    remaining -= count * int(item["price_now"])
            if picks:
                for iid, name, count, price in picks:
                    st.write(f"• {name} × {count} — ₹{count * price}")
                    if st.button(f"Add {name} to cart", key=f"budget_add_{iid}"):
                        cart[iid] = min(int(cart.get(iid, 0)) + count, int(available[available['item_id'].astype(int) == iid].iloc[0]['quantity']))
                        st.toast("Added suggested item to cart", icon="🛒")
                st.caption(f"Estimated total: ₹{budget - remaining} · Remaining budget: ₹{remaining}")
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
                # Keep the pickup code in this student's session so it can be
                # displayed after the confirmation dialog is dismissed.
                st.session_state["_latest_pickup"] = {
                    "order_id": int(res["order_id"]),
                    "item_name": str(res["item_name"]),
                    "qty": int(res["qty"]),
                    "pickup_code": str(res["pickup_code"]).zfill(6),
                    "status": "Pending",
                }
                st.session_state["_show_order_success"] = True
                st.rerun()
            else:
                st.error(msg)

        if st.session_state.get("_show_order_success", False):
            show_order_success_dialog()

        # Show the pickup code at the bottom of the Order Food page.
        # The student reads this code to the canteen worker at collection.
        latest_pickup = st.session_state.get("_latest_pickup")
        if latest_pickup:
            # Refresh the order status so a collected/cancelled code is no
            # longer presented as valid when the student returns to this page.
            student_orders_now = core.student_orders(user["user_id"])
            matching_order = student_orders_now[
                student_orders_now["order_id"].astype(str) == str(latest_pickup["order_id"])
            ] if len(student_orders_now) else student_orders_now
            if not matching_order.empty:
                latest_pickup["status"] = str(matching_order.iloc[0]["status"])
                st.session_state["_latest_pickup"] = latest_pickup

        if latest_pickup and latest_pickup.get("status") == "Pending":
            st.markdown(
                f"""
                <div class="fl-card" style="padding: 1.5rem; margin-top: 2rem; border: 2px solid #F26B1D; background: linear-gradient(145deg, #FFFFFF, #FFF4EA);">
                    <div style="text-align:center;">
                        <div style="font-size:.78rem; font-weight:800; letter-spacing:2px; color:#F26B1D;">YOUR PICKUP VERIFICATION CODE</div>
                        <div style="font-size:2.8rem; font-weight:900; letter-spacing:12px; color:#1F1B2D; margin: .65rem 0;">{latest_pickup['pickup_code']}</div>
                        <div style="font-size:1rem; font-weight:700; color:#1F1B2D;">Order #{latest_pickup['order_id']} · {latest_pickup['item_name']} × {latest_pickup['qty']}</div>
                        <div style="font-size:.9rem; color:#6B7280; margin-top:.6rem;">Show this code to the canteen worker when collecting your order. Keep it private until pickup.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        ui.footer()

    def student_wallet():
        flash = st.session_state.pop("_flash", None)
        if flash:
            getattr(st, flash[0])(flash[1])
        w = core.wallet_summary(user["user_id"])
        pending = core.pending_points(user["user_id"])

        ui.hero("FoodLoop Wallet", "Balance", "Track your eco-points and transactions.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Available points", w["balance"])
        m2.metric("Total earned", w["earned"])
        m3.metric("Total redeemed", w["redeemed"])
        m4.metric("Pending points", pending)

        st.subheader("Transaction history")
        st.dataframe(w["history"], hide_index=True, width="stretch")

        ui.footer()

    def student_my_orders():
        ui.hero("My Orders", "History", "View your previous purchases, current order status and pickup codes.")
        orders = core.student_orders(user["user_id"])
        if orders.empty:
            st.info("You haven't placed any orders yet. Explore current surplus deals to get started.")
            ui.footer()
            return

        status_filter = st.selectbox("Filter orders", ["All", "Pending", "Collected", "Cancelled", "Expired"], key="my_orders_status")
        shown = orders.copy()
        if status_filter != "All":
            shown = shown[shown["status"].astype(str).str.lower() == status_filter.lower()]
        shown = shown.sort_values("created_at", ascending=False)
        if shown.empty:
            st.info("No orders match this status.")
        for _, row in shown.iterrows():
            oid = int(row["order_id"])
            status = str(row["status"])
            badge_html = ui.status_badge(status)
            st.markdown(
                f"""
                <div class="fl-card" style="padding: 1.25rem; margin-bottom:.8rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:1rem;">
                        <div><span style="font-size:1.12rem; font-weight:800; color:#1F1B2D;">{row['item_name']}</span>
                        <span style="color:#6B7280; font-weight:600; margin-left:8px;">× {int(row['qty'])}</span></div>
                        <div>{badge_html}</div>
                    </div>
                    <div style="display:flex; justify-content:space-between; color:#4B5563; font-size:.95rem; margin-top:.55rem;">
                        <span>Order #{oid} · {str(row['created_at'])[:16]}</span>
                        <span>Total paid: <b style="color:#F26B1D;">₹{int(row['total_paid'])}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True,
            )
            if status == "Pending" and "pickup_code" in row.index and str(row.get("pickup_code", "")).strip():
                st.info(f"Pickup code for Order #{oid}: **{str(row['pickup_code']).zfill(6)}** — show this to the canteen worker at collection.")
                if st.button("Cancel order", key=f"my_order_cancel_{oid}", width="stretch"):
                    ok, msg = core.cancel_order(oid, user["user_id"], user["role"])
                    if ok:
                        st.session_state["_flash"] = ("success", msg)
                        st.rerun()
                    st.error(msg)
        ui.footer()

    def student_reviews():
        orders = core.student_orders(user["user_id"])
        collected = orders[orders["status"] == "Collected"] if len(orders) else orders
        st.subheader("Rate your collected orders")
        reviewed = set(core.read("reviews")["order_id"].astype(str).tolist()) if len(core.read("reviews")) else set()
        pending_review = collected[~collected["order_id"].astype(str).isin(reviewed)] if len(collected) else collected
        if pending_review.empty:
            st.info("No collected orders waiting for a review.")
        else:
            for _, order in pending_review.iterrows():
                oid = int(order["order_id"])
                with st.expander(f"{order['item_name']} · Order #{oid}"):
                    rating = st.select_slider("Rating", options=[1, 2, 3, 4, 5], value=5, key=f"review_rating_{oid}")
                    comment = st.text_area("Your review (optional)", key=f"review_text_{oid}", placeholder="How was the food?")
                    if st.button("Submit review", key=f"submit_review_{oid}"):
                        ok, msg = core.add_review(user["user_id"], oid, rating, comment)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.rerun()
        st.subheader("Your submitted reviews")
        all_reviews = core.read("reviews")
        mine = all_reviews[all_reviews["user_id"].astype(str) == str(user["user_id"])] if len(all_reviews) else all_reviews
        if len(mine):
            st.dataframe(mine[["item_name", "rating", "review", "created_at"]], hide_index=True, width="stretch")

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

        f = core.forecast(vendor_id=user["user_id"])
        if not f.empty:
            st.subheader("Quick waste forecast")
            for msg in f["advice"].head(2):
                st.info("💡 " + msg)

        ui.footer()

    def vendor_add_surplus():
        ui.hero("Add Surplus", "Listings", "Publish fresh unsold food portions with automatic dynamic discounts.")

        # These controls are intentionally outside a form so changing the
        # category immediately refreshes the available food choices.
        category = st.selectbox("Food category", list(core.FOOD_MENU.keys()), key="vendor_food_category")
        food_options = core.FOOD_MENU[category]
        selected_food = st.selectbox(
            "Select food item", food_options + ["Other / Custom item"],
            key="vendor_selected_food"
        )

        if selected_food == "Other / Custom item":
            name = st.text_input("Enter food name", placeholder="e.g. Mushroom Fried Rice", key="vendor_custom_food")
            default_price = 80
        else:
            name = selected_food
            default_price = int(core.FOOD_PRICES.get(selected_food, 80))

        mrp = st.number_input("MRP (₹)", min_value=1, max_value=2000, value=default_price, key="vendor_food_mrp")
        qty = st.number_input("Portions available", min_value=1, max_value=500, value=10, key="vendor_food_qty")
        hrs = st.slider("Valid for (hours)", 0.5, 6.0, 2.0, 0.5, key="vendor_food_hours")
        if st.button("Publish Surplus Listing", width="stretch", type="primary"):
            row, msg = core.add_item(user["user_id"], name, mrp, qty, hrs)
            if row:
                st.success(msg)
                st.rerun()
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
        st.caption("Based on real orders when available; demo history otherwise.")
        f = core.forecast(vendor_id=user["user_id"])
        if f.empty:
            st.info("Not enough preparation history yet.")
        else:
            for _, row in f.iterrows():
                conf = row.get("confidence", "Medium")
                trend = row.get("trend", "none")
                trend_str = f" &bull; Trend: {trend}" if trend != "none" else ""
                st.info(f"💡 {row['advice']} (**{conf} confidence**{trend_str})")
            st.dataframe(f, hide_index=True, width="stretch")

        ui.footer()

    # ---------------- Routing ----------------
    if page == "Logout":
        clear_session()
        st.toast("You have been logged out.", icon="👋")
        st.rerun()

    routes = {
        # Student routes
        "Explore Deals": student_explore,
        "My Orders": student_my_orders,
        "Wallet": student_wallet,
        "Reviews": student_reviews,
        "Refer a Friend": student_referral,
        "Cart": student_cart,
        # Vendor routes
        "Overview": vendor_overview,
        "Add Surplus": vendor_add_surplus,
        "Orders & Pickup": vendor_orders_page,
        "Sales & Forecast": vendor_sales_forecast,
    }

    routes[page]()
