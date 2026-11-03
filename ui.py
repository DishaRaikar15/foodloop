"""FoodLoop UI components and design system: modern orange food-delivery theme."""
import io
import streamlit as st

try:
    import qrcode
except ImportError:
    qrcode = None

import core


def inject_css():
    """Inject modern orange food-delivery stylesheet."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1F1B2D;
        }

        /* Page gradient: soft peach to white */
        .stApp {
            background: linear-gradient(180deg, #FFF4EA 0%, #FFFFFF 650px, #FFFFFF 100%) !important;
            color: #1F1B2D;
        }

        /* Hide Streamlit default header, footer, menu, deploy button */
        #MainMenu {visibility: hidden; display: none !important;}
        footer {visibility: hidden; display: none !important;}
        header {visibility: hidden; display: none !important;}
        [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
        .stDeployButton {display: none !important;}

        /* Tidy 1100px max content width */
        .block-container {
            max-width: 1100px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 3.5rem !important;
            margin: 0 auto !important;
        }

        /* Large Headings: hero 3rem, weight 800 */
        .fl-hero-title {
            font-size: 3rem !important;
            font-weight: 800 !important;
            color: #1F1B2D !important;
            line-height: 1.15 !important;
            letter-spacing: -1px !important;
            margin-bottom: 0.5rem !important;
        }

        /* Squiggle underline for highlighted word */
        .fl-highlight {
            color: #F26B1D !important;
            text-decoration: underline wavy #F26B1D !important;
            text-underline-offset: 8px !important;
            text-decoration-thickness: 3px !important;
        }

        /* White sections with 24px radius and soft shadow */
        .fl-section, .fl-card {
            background: #FFFFFF;
            border-radius: 24px;
            box-shadow: 0 4px 20px rgba(31, 27, 45, 0.06);
            border: 1px solid rgba(255, 232, 214, 0.7);
            margin-bottom: 1.25rem;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .fl-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(242, 107, 29, 0.12);
        }

        /* Orange pill buttons with white text (hover: slightly darker #D8580F) */
        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            background-color: #F26B1D !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border-radius: 9999px !important;
            border: none !important;
            padding: 0.55rem 1.4rem !important;
            font-size: 0.95rem !important;
            box-shadow: 0 4px 14px rgba(242, 107, 29, 0.25) !important;
            transition: all 0.2s ease !important;
        }

        div.stButton > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            background-color: #D8580F !important;
            color: #FFFFFF !important;
            box-shadow: 0 6px 18px rgba(216, 88, 15, 0.35) !important;
            transform: translateY(-1px);
        }

        div.stButton > button:active,
        div[data-testid="stFormSubmitButton"] > button:active {
            transform: translateY(0);
        }

        /* Secondary buttons (e.g. inactive category tiles) */
        div.stButton > button[kind="secondary"] {
            background-color: #FFFFFF !important;
            color: #1F1B2D !important;
            border: 1.5px solid #FFE8D6 !important;
            box-shadow: 0 2px 8px rgba(31, 27, 45, 0.04) !important;
        }

        div.stButton > button[kind="secondary"]:hover {
            background-color: #FFF4EA !important;
            border-color: #F26B1D !important;
            color: #F26B1D !important;
        }

        /* Style st.radio(horizontal=True) as a top navbar of text links with an orange underline on active link */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 1.75rem !important;
            border-bottom: 2px solid #FFE8D6 !important;
            padding-bottom: 0.5rem !important;
            margin-bottom: 1.5rem !important;
        }

        div[data-testid="stRadio"] label {
            cursor: pointer !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            color: #6B7280 !important;
            padding: 0.35rem 0.5rem 0.5rem 0.5rem !important;
            border-bottom: 3px solid transparent !important;
            margin-bottom: -2px !important;
            transition: all 0.15s ease !important;
            background: transparent !important;
        }

        div[data-testid="stRadio"] label:hover {
            color: #F26B1D !important;
        }

        div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        div[data-testid="stRadio"] label:has(input:checked),
        div[data-testid="stRadio"] label[aria-checked="true"] {
            color: #F26B1D !important;
            border-bottom: 3px solid #F26B1D !important;
            font-weight: 700 !important;
        }

        /* Pill Badges */
        .fl-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .fl-badge-discount {
            background-color: #E8F8F1;
            color: #1FA971;
        }

        .fl-badge-urgent {
            background-color: #FDE8E8;
            color: #E5484D;
            font-weight: 800;
            border: 1px solid #FCA5A5;
        }

        .fl-badge-time {
            background-color: rgba(255, 255, 255, 0.95);
            color: #4B5563;
            border: 1px solid #E2E8F0;
        }

        .fl-badge-points {
            background-color: #FFF4EA;
            color: #F26B1D;
            border: 1px solid #FCD3B6;
        }

        /* Centered Metric Tiles */
        [data-testid="stMetric"] {
            background: #FFFFFF !important;
            border-radius: 24px !important;
            padding: 1.25rem 1rem !important;
            box-shadow: 0 4px 18px rgba(31, 27, 45, 0.05) !important;
            border: 1px solid #FFE8D6 !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
        }

        [data-testid="stMetricLabel"] {
            width: 100% !important;
            justify-content: center !important;
            text-align: center !important;
            color: #6B7280 !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
        }

        [data-testid="stMetricLabel"] > div {
            justify-content: center !important;
        }

        [data-testid="stMetricValue"] {
            width: 100% !important;
            justify-content: center !important;
            text-align: center !important;
            color: #1F1B2D !important;
            font-size: 2.1rem !important;
            font-weight: 800 !important;
            margin-top: 0.25rem !important;
        }

        [data-testid="stMetricValue"] > div {
            justify-content: center !important;
        }

        /* 6-digit Code Box */
        .fl-code-box {
            display: flex;
            gap: 8px;
            justify-content: center;
            align-items: center;
            margin: 10px 0 14px 0;
        }

        .fl-code-digit {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 52px;
            background: #FFF4EA;
            border: 2px solid #F26B1D;
            border-radius: 12px;
            font-size: 1.6rem;
            font-weight: 800;
            color: #1F1B2D;
            font-family: monospace, sans-serif;
            box-shadow: inset 0 2px 4px rgba(242, 107, 29, 0.12);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def navbar(brand: str = "FoodLoop"):
    """Render top brand identity above navigation."""
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 0.5rem 0 0.75rem 0;">
            <span style="display: inline-block; width: 14px; height: 14px; background-color: #F26B1D; border-radius: 50%;"></span>
            <span style="font-size: 1.6rem; font-weight: 800; color: #1F1B2D; letter-spacing: -0.5px;">{brand}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(headline: str, highlight_word: str, subtitle: str = ""):
    """Render large hero headline with CSS squiggle underline on the highlight word."""
    sub_html = f"<p style='font-size: 1.15rem; color: #6B7280; font-weight: 500; margin-top: 0.5rem; line-height: 1.5;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div style="margin: 0.75rem 0 1.25rem 0;">
            <h1 class="fl-hero-title">
                {headline} <span class="fl-highlight">{highlight_word}</span>
            </h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def impact_pill(portions: int, co2_kg: float):
    """Small white rounded pill under search bar showing impact metrics."""
    st.markdown(
        f"""
        <div style="display: inline-flex; align-items: center; gap: 10px; background: #FFFFFF; border: 1px solid #FFE8D6; box-shadow: 0 2px 10px rgba(31, 27, 45, 0.05); border-radius: 9999px; padding: 7px 18px; margin: 0.4rem 0 1.25rem 0; font-size: 0.9rem; color: #4B5563; font-weight: 600;">
            <span>🌱 <b>{portions}</b> portions saved</span>
            <span style="color: #CBD5E1;">&bull;</span>
            <span>💨 <b>{co2_kg} kg</b> CO₂ avoided</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def category_tiles() -> str:
    """Row of 5 category tiles (All, Meals, Rolls, Snacks, South Indian). Stored in session state."""
    cats = [
        ("All", "🍽️"),
        ("Meals", "🍛"),
        ("Rolls", "🌯"),
        ("Snacks", "🥟"),
        ("South Indian", "🥞"),
    ]
    if "selected_category" not in st.session_state:
        st.session_state["selected_category"] = "All"

    cols = st.columns(len(cats))
    for i, (name, icon) in enumerate(cats):
        is_active = st.session_state["selected_category"] == name
        btn_label = f"{icon} {name}"
        btn_type = "primary" if is_active else "secondary"
        if cols[i].button(btn_label, key=f"cat_tile_{name}", width="stretch", type=btn_type):
            st.session_state["selected_category"] = name
            st.rerun()

    return st.session_state.get("selected_category", "All")


def deal_card(row):
    """HTML card with peach rounded top area, keyword emoji, countdown pill, discount badge, bold price, and points pill."""
    name = row.get("name", "Item")
    n_lower = str(name).lower()
    if "thali" in n_lower or "meal" in n_lower:
        emoji = "🍛"
    elif "roll" in n_lower or "wrap" in n_lower:
        emoji = "🌯"
    elif "samosa" in n_lower:
        emoji = "🥟"
    elif "dosa" in n_lower:
        emoji = "🥞"
    else:
        emoji = "🍽️"

    mrp = int(row.get("mrp", 0))
    price_now = int(row.get("price_now", 0))
    group_price = int(row.get("group_price", price_now))
    quantity = int(row.get("quantity", 0))
    minutes_left = int(row.get("minutes_left", 0))
    discount_pct = int(row.get("discount_%", 0))
    pts = price_now // core.POINTS_PER_RUPEES

    time_badge_class = "fl-badge fl-badge-urgent" if minutes_left < 30 else "fl-badge fl-badge-time"

    st.markdown(
        f"""
        <div class="fl-card" style="padding: 1rem; border-radius: 24px; margin-bottom: 0.75rem;">
            <div style="background: #FFE8D6; border-radius: 18px; padding: 1.5rem 1rem; position: relative; display: flex; align-items: center; justify-content: center; min-height: 120px;">
                <span class="fl-badge fl-badge-discount" style="position: absolute; top: 10px; left: 10px;">-{discount_pct}%</span>
                <span class="{time_badge_class}" style="position: absolute; top: 10px; right: 10px;">⏱ {minutes_left} min</span>
                <div style="font-size: 3.2rem; line-height: 1;">{emoji}</div>
            </div>
            <div style="padding: 0.85rem 0.25rem 0.25rem 0.25rem;">
                <div style="font-size: 1.15rem; font-weight: 800; color: #1F1B2D; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{name}</div>
                <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px;">
                    <span style="font-size: 1.4rem; font-weight: 800; color: #F26B1D;">₹{price_now}</span>
                    <span style="font-size: 0.95rem; color: #9CA3AF; text-decoration: line-through;">₹{mrp}</span>
                    <span style="font-size: 0.85rem; font-weight: 700; color: #6B7280; margin-left: auto;">{quantity} left</span>
                </div>
                <div style="font-size: 0.85rem; color: #4B5563; margin-bottom: 8px;">
                    Group deal: <b>₹{group_price}</b> ({core.GROUP_MIN_QTY}+ portions)
                </div>
                <div>
                    <span class="fl-badge fl-badge-points">⭐ earn {pts} pts</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def promo_banner(title: str, subtitle: str = ""):
    """Orange gradient promo banner with white text."""
    sub_html = f"<p style='color: rgba(255, 255, 255, 0.95) !important; font-size: 1.05rem; margin: 0; font-weight: 500;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #F26B1D 0%, #FF8A3D 100%); border-radius: 24px; padding: 1.75rem 2rem; color: #FFFFFF; margin: 2rem 0; box-shadow: 0 8px 24px rgba(242, 107, 29, 0.25);">
            <h3 style="color: #FFFFFF !important; font-size: 1.45rem; font-weight: 800; margin: 0 0 0.35rem 0;">{title}</h3>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def pickup_card(order):
    """Show order ID, item name, QR image of pickup code, and 6-digit code in spaced boxes."""
    oid = int(order.get("order_id", 0))
    item = order.get("item_name", "Food Order")
    qty = order.get("qty")
    qty_str = f" &times; {int(qty)}" if qty else ""
    code = str(order.get("pickup_code", "")).zfill(6)
    digits_html = "".join(f"<div class='fl-code-digit'>{d}</div>" for d in code)

    st.markdown(
        f"""
        <div class="fl-card" style="text-align: center; max-width: 440px; margin: 1rem auto 0 auto; padding: 1.5rem 1.25rem 1rem 1.25rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #F26B1D; text-transform: uppercase; letter-spacing: 0.5px;">Pickup Pass</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #1F1B2D; margin: 4px 0 2px 0;">Order #{oid}</div>
            <div style="font-size: 1.05rem; font-weight: 600; color: #4B5563; margin-bottom: 10px;">{item}{qty_str}</div>
            <div class="fl-code-box">{digits_html}</div>
            <div style="font-size: 0.85rem; color: #6B7280; margin-bottom: 8px;">Show this code or scan QR at the counter</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if qrcode is not None:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1F1B2D", back_color="#FFFFFF")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        c1, c2, c3 = st.columns([1, 1, 1])
        c2.image(buf, width=160)


def status_badge(status: str) -> str:
    """Return colored pill HTML for order status: Pending amber, Collected green, Cancelled grey."""
    s = str(status)
    if s == "Pending":
        return '<span style="background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 0.82rem;">Pending</span>'
    elif s == "Collected":
        return '<span style="background-color: #E8F8F1; color: #1FA971; border: 1px solid #A7F3D0; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 0.82rem;">Collected</span>'
    else:
        return '<span style="background-color: #F3F4F6; color: #6B7280; border: 1px solid #E5E7EB; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 0.82rem;">Cancelled</span>'


def footer():
    """Slim footer bar reading: FoodLoop - Samsung Innovation Lab."""
    st.markdown(
        """
        <div style="text-align: center; color: #9CA3AF; font-size: 0.85rem; font-weight: 500; border-top: 1px solid #FFE8D6; padding: 1.75rem 0 1.25rem 0; margin-top: 3rem;">
            FoodLoop &bull; Samsung Innovation Lab
        </div>
        """,
        unsafe_allow_html=True,
    )
