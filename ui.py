"""FoodLoop UI components and design system: amber theme, cards, hero banners, and QR pickup codes."""
import io
import streamlit as st

try:
    import qrcode
except ImportError:
    qrcode = None

import core


def inject_css():
    """Inject modern amber/yellow food-app stylesheet."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1F1B2D;
        }

        /* Hide Streamlit default header, footer, menu, deploy button */
        #MainMenu {visibility: hidden; display: none !important;}
        footer {visibility: hidden; display: none !important;}
        header {visibility: hidden; display: none !important;}
        [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
        .stDeployButton {display: none !important;}

        /* Amber Gradient Hero Banner */
        .fl-hero {
            background: linear-gradient(135deg, #FDB913 0%, #F59E0B 100%);
            border-radius: 24px;
            padding: 1.75rem 2rem;
            color: #1F1B2D;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(253, 185, 19, 0.22);
        }

        .fl-hero h1, .fl-hero h2 {
            color: #1F1B2D !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px;
            margin: 0;
        }

        .fl-hero p {
            color: #1F1B2D !important;
            font-size: 1.05rem;
            font-weight: 500;
            margin: 0.4rem 0 0 0;
            opacity: 0.95;
        }

        /* White Cards with 24px radius and soft shadow */
        .fl-card {
            background: #FFFFFF;
            border-radius: 24px;
            padding: 1.4rem;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05);
            border: 1px solid rgba(253, 185, 19, 0.15);
            margin-bottom: 1rem;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .fl-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 28px rgba(253, 185, 19, 0.18);
        }

        /* Pill Badges */
        .fl-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 700;
            line-height: 1.3;
        }

        /* Discount = Green */
        .fl-badge-discount {
            background-color: #DEF7EC;
            color: #03543F;
        }

        /* Points = Amber with a dark star */
        .fl-badge-points {
            background-color: #FEF3C7;
            color: #92400E;
            border: 1px solid #FCD34D;
        }

        /* Time countdown pills: normal grey, red under 30 mins */
        .fl-badge-time {
            background-color: #F3F4F6;
            color: #374151;
        }

        .fl-badge-time-low {
            background-color: #FDE8E8;
            color: #9B1C1C;
            border: 1px solid #F87171;
            animation: fl-pulse 2s infinite ease-in-out;
        }

        @keyframes fl-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
        }

        /* Order Status Badges */
        .fl-badge-status-pending {
            background-color: #FEF3C7;
            color: #92400E;
            border: 1px solid #FCD34D;
        }
        .fl-badge-status-collected {
            background-color: #DEF7EC;
            color: #03543F;
            border: 1px solid #A7F3D0;
        }
        .fl-badge-status-cancelled {
            background-color: #F3F4F6;
            color: #6B7280;
            border: 1px solid #E5E7EB;
        }

        /* Rounded Buttons in Amber with Dark Text */
        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            background-color: #FDB913 !important;
            color: #1F1B2D !important;
            font-weight: 700 !important;
            border-radius: 9999px !important;
            border: none !important;
            padding: 0.55rem 1.4rem !important;
            font-size: 0.95rem !important;
            box-shadow: 0 4px 12px rgba(253, 185, 19, 0.3) !important;
            transition: all 0.2s ease !important;
        }

        div.stButton > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            background-color: #F59E0B !important;
            color: #1F1B2D !important;
            box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4) !important;
            transform: translateY(-1px);
        }

        div.stButton > button:active,
        div[data-testid="stFormSubmitButton"] > button:active {
            transform: translateY(0);
        }

        /* Large Centered Metric Tiles */
        [data-testid="stMetric"] {
            background: #FFFFFF !important;
            border-radius: 24px !important;
            padding: 1.25rem 1rem !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05) !important;
            border: 1px solid rgba(253, 185, 19, 0.15) !important;
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
            color: #4B5563 !important;
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
            font-size: 2rem !important;
            font-weight: 800 !important;
            margin-top: 0.25rem !important;
        }

        [data-testid="stMetricValue"] > div {
            justify-content: center !important;
        }

        /* Chip-style buttons / pills styling */
        [data-testid="stPills"] {
            gap: 8px;
            margin: 0.5rem 0 1rem 0;
        }

        [data-testid="stPills"] button {
            border-radius: 9999px !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 0.35rem 1rem !important;
        }

        /* Pickup Code Display Boxes */
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
            background: #FFF8E7;
            border: 2px solid #FDB913;
            border-radius: 12px;
            font-size: 1.6rem;
            font-weight: 800;
            color: #1F1B2D;
            font-family: monospace, sans-serif;
            box-shadow: inset 0 2px 4px rgba(253, 185, 19, 0.15);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str = ""):
    """Render an amber gradient banner with title and optional subtitle."""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="fl-hero">
            <h2>{title}</h2>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def food_card(row):
    """Render an HTML card for a surplus food item."""
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

    time_badge_class = "fl-badge fl-badge-time-low" if minutes_left < 30 else "fl-badge fl-badge-time"

    st.markdown(
        f"""
        <div class="fl-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div style="font-size: 2.2rem; line-height: 1;">{emoji}</div>
                <span style="font-size: 0.85rem; font-weight: 700; color: #4B5563; background: #FFF8E7; border: 1px solid #FCD34D; padding: 3px 10px; border-radius: 9999px;">{quantity} left</span>
            </div>
            <div style="font-size: 1.25rem; font-weight: 800; color: #1F1B2D; margin-bottom: 6px;">{name}</div>
            <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;">
                <span style="font-size: 1.45rem; font-weight: 800; color: #1F1B2D;">₹{price_now}</span>
                <span style="font-size: 1rem; color: #9CA3AF; text-decoration: line-through;">₹{mrp}</span>
                <span class="fl-badge fl-badge-discount">-{discount_pct}%</span>
            </div>
            <div style="font-size: 0.88rem; color: #4B5563; margin-bottom: 12px;">
                Group deal: <b>₹{group_price}</b> each ({core.GROUP_MIN_QTY}+ portions)
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                <span class="{time_badge_class}">⏱ {minutes_left} min left</span>
                <span class="fl-badge fl-badge-points">⭐ earn {pts} pts</span>
            </div>
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
            <div style="font-size: 0.82rem; font-weight: 700; color: #92400E; text-transform: uppercase; letter-spacing: 0.5px;">Pickup Pass</div>
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


def points_chip(balance: int, pending: int = 0):
    """Render an amber badge showing balance and pending points."""
    pending_html = (
        f"<span style='font-size: 0.82rem; color: #78350F; background: rgba(253, 185, 19, 0.35); padding: 2px 8px; border-radius: 9999px; font-weight: 600; margin-left: 6px;'>+{pending} pending</span>"
        if pending > 0 else ""
    )
    st.markdown(
        f"""
        <div style="display: inline-flex; align-items: center; background: #FEF3C7; border: 1.5px solid #FCD34D; color: #92400E; padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 0.95rem; box-shadow: 0 2px 6px rgba(253, 185, 19, 0.15); margin-bottom: 1rem;">
            <span>⭐ {balance} pts</span>
            {pending_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
