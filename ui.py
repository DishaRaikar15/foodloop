"""
FoodLoop UI components and design system.
Modern orange food-delivery theme with white dropdowns and form controls.
"""

import io
import streamlit as st

try:
    import qrcode
except ImportError:
    qrcode = None

import core


def _flat(html: str) -> str:
    """Collapse HTML onto one line.

    Markdown ends an HTML block at a blank line and treats lines indented
    by 4+ spaces as code. Stripping every line and joining with a space
    guarantees the HTML always renders instead of showing as code.
    """
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


# ============================================================
# GLOBAL CSS
# ============================================================

def inject_css():
    """Apply FoodLoop styling across the entire Streamlit application."""

    st.markdown(
        """
        <style>

        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        /* ---------------- GLOBAL THEME ---------------- */

        :root {
            color-scheme: light !important;
        }

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #1F1B2D !important;
        }

        .stApp {
            background: linear-gradient(
                180deg,
                #FFF4EA 0%,
                #FFFFFF 650px,
                #FFFFFF 100%
            ) !important;
            color: #1F1B2D !important;
        }

        /* Hide Streamlit header and footer */

        #MainMenu,
        footer,
        header,
        [data-testid="stToolbar"],
        .stDeployButton {
            visibility: hidden !important;
            display: none !important;
        }

        .block-container {
            max-width: 1100px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 3.5rem !important;
            margin: auto !important;
        }

        /* ---------------- HEADINGS ---------------- */

        h1, h2, h3, h4, h5, h6 {
            color: #1F1B2D !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .fl-hero-title {
            font-size: 3rem !important;
            font-weight: 800 !important;
            color: #1F1B2D !important;
            line-height: 1.15 !important;
            letter-spacing: -1px !important;
            margin-bottom: 0.5rem !important;
        }

        .fl-highlight {
            color: #F26B1D !important;
            text-decoration: underline wavy #F26B1D !important;
            text-underline-offset: 8px !important;
            text-decoration-thickness: 3px !important;
        }

        /* ---------------- SECTIONS AND CARDS ---------------- */

        .fl-section,
        .fl-card {
            background: #FFFFFF !important;
            border-radius: 24px !important;
            box-shadow: 0 4px 20px rgba(31, 27, 45, 0.06) !important;
            border: 1px solid rgba(255, 232, 214, 0.7) !important;
            margin-bottom: 1.25rem !important;
            color: #1F1B2D !important;
        }

        .fl-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(242, 107, 29, 0.12) !important;
        }

        /* ---------------- FORM LABELS ---------------- */

        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        .stSelectbox label,
        .stNumberInput label,
        .stTextInput label,
        .stSlider label,
        .stTextArea label,
        .stRadio label {
            color: #1F1B2D !important;
            font-weight: 400 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        /* ---------------- DROPDOWN: CLOSED STATE ---------------- */

        /* Main selectbox container */

        div[data-baseweb="select"] {
            background-color: #FFFFFF !important;
            color: #1F1B2D !important;
            border-radius: 14px !important;
        }

        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            color: #1F1B2D !important;
            border: 1.5px solid #FFE0C7 !important;
            border-radius: 14px !important;
            min-height: 48px !important;
            box-shadow: none !important;
        }

        /* Dropdown selected text */

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] div {
            color: #1F1B2D !important;
        }

        div[data-baseweb="select"] input {
            background-color: transparent !important;
            -webkit-text-fill-color: #1F1B2D !important;
        }

        /* Dropdown arrow */

        div[data-baseweb="select"] svg {
            fill: #1F1B2D !important;
            color: #1F1B2D !important;
        }

        /* Orange border when focused */

        div[data-baseweb="select"]:focus-within > div {
            border: 1.5px solid #F26B1D !important;
            box-shadow: 0 0 0 1px #F26B1D !important;
        }

        /* Force white closed selectbox on newer Streamlit versions
           (extra wrapper divs are nested inside baseweb select) */

        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
        [data-testid="stSelectbox"] [data-baseweb="select"] input {
            background-color: #FFFFFF !important;
            color: #1F1B2D !important;
            -webkit-text-fill-color: #1F1B2D !important;
        }

        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            border: none !important;
            box-shadow: 0 1px 6px rgba(31, 27, 45, 0.06) !important;
        }

        [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within > div {
            box-shadow: 0 0 0 1.5px #F26B1D !important;
        }

        /* ---------------- DROPDOWN: OPEN STATE ---------------- */

        /* Dropdown popup */

        div[data-baseweb="popover"] {
            background-color: #FFF3E9 !important;
            border-radius: 16px !important;
            border: 1px solid #FFE0C7 !important;
            box-shadow: 0 10px 30px rgba(31, 27, 45, 0.12) !important;
            overflow: hidden !important;
        }

        /* Dropdown list */

        div[data-baseweb="popover"] ul,
        ul[role="listbox"] {
            background-color: #FFF3E9 !important;
            color: #1F1B2D !important;
            border-radius: 16px !important;
            padding: 5px !important;
        }

        /* Individual dropdown options */

        div[data-baseweb="popover"] li,
        li[role="option"] {
            background-color: #FFF3E9 !important;
            color: #1F1B2D !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            padding: 14px 16px !important;
            border-radius: 8px !important;
            cursor: pointer !important;
        }

        /* Hovered option */

        div[data-baseweb="popover"] li:hover,
        li[role="option"]:hover {
            background-color: #FFE9D4 !important;
            color: #1F1B2D !important;
        }

        /* Selected option */

        div[data-baseweb="popover"] li[aria-selected="true"],
        li[role="option"][aria-selected="true"] {
            background-color: #FFE9D4 !important;
            color: #1F1B2D !important;
            font-weight: 700 !important;
        }

        /* Dropdown option text */

        div[data-baseweb="popover"] li *,
        li[role="option"] * {
            color: #1F1B2D !important;
        }

        /* ---------------- NUMBER INPUTS ---------------- */

        div[data-testid="stNumberInput"] {
            background: transparent !important;
        }

        div[data-testid="stNumberInput"] div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border: none !important;
            border-radius: 6px !important;
            box-shadow: 0 1px 6px rgba(31, 27, 45, 0.06) !important;
        }

        div[data-testid="stNumberInput"] input {
            background-color: #FFFFFF !important;
            color: #1F1B2D !important;
            -webkit-text-fill-color: #1F1B2D !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        div[data-testid="stNumberInput"] button {
            background: transparent !important;
            border: none !important;
            color: #1F1B2D !important;
        }

        div[data-testid="stNumberInput"] button:hover {
            background: #FFF3E9 !important;
            color: #F26B1D !important;
        }

        /* ---------------- TEXT INPUTS ---------------- */

        div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border: 1.5px solid #FFE0C7 !important;
            border-radius: 12px !important;
        }

        div[data-baseweb="input"] input {
            background-color: #FFFFFF !important;
            color: #1F1B2D !important;
            -webkit-text-fill-color: #1F1B2D !important;
        }

        div[data-baseweb="input"]:focus-within {
            border-color: #F26B1D !important;
            box-shadow: 0 0 0 1px #F26B1D !important;
        }

        /* Number input wrapper keeps the borderless look
           (declared after the generic text-input rule so it wins) */

        div[data-testid="stNumberInput"] div[data-baseweb="input"] {
            border: none !important;
            border-radius: 6px !important;
        }

        /* ---------------- TEXT AREA ---------------- */

        div[data-baseweb="textarea"] {
            background-color: #FFFFFF !important;
            border: 1.5px solid #FFE0C7 !important;
            border-radius: 12px !important;
        }

        div[data-baseweb="textarea"] textarea {
            background-color: #FFFFFF !important;
            color: #1F1B2D !important;
            -webkit-text-fill-color: #1F1B2D !important;
        }

        /* ---------------- SLIDER ---------------- */

        div[data-testid="stSlider"] {
            color: #F26B1D !important;
        }

        div[data-testid="stSlider"] [role="slider"] {
            background-color: #F26B1D !important;
            border-color: #F26B1D !important;
        }

        div[data-testid="stSlider"] [data-testid="stTickBar"] {
            background-color: #FFE0C7 !important;
        }

        /* ---------------- BUTTONS ---------------- */

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
            transform: translateY(-1px);
        }

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

        /* ---------------- RADIO NAVIGATION ---------------- */

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
            padding: 0.35rem 0.5rem 0.5rem !important;
            background: transparent !important;
        }

        div[data-testid="stRadio"] label:hover {
            color: #F26B1D !important;
        }

        div[data-testid="stRadio"] label:has(input:checked),
        div[data-testid="stRadio"] label[aria-checked="true"] {
            color: #F26B1D !important;
            border-bottom: 3px solid #F26B1D !important;
            font-weight: 700 !important;
        }

        /* Top navigation only (radio with key="nav_page"):
           hide the radio circles so it looks like plain tabs */

        .st-key-nav_page label > div:first-child {
            display: none !important;
        }

        .st-key-nav_page label {
            padding: 0.35rem 0.5rem 0.5rem !important;
        }

        .st-key-nav_page label p {
            font-weight: 500 !important;
            color: #1F1B2D !important;
        }

        .st-key-nav_page label:has(input:checked) p {
            color: #F26B1D !important;
            font-weight: 600 !important;
        }

        /* ---------------- BADGES ---------------- */

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
            background-color: #FFFFFF;
            color: #4B5563;
            border: 1px solid #E2E8F0;
        }

        .fl-badge-points {
            background-color: #FFF4EA;
            color: #F26B1D;
            border: 1px solid #FCD3B6;
        }

        /* ---------------- METRIC TILES ---------------- */

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
            color: #6B7280 !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
        }

        [data-testid="stMetricValue"] {
            color: #1F1B2D !important;
            font-size: 2.1rem !important;
            font-weight: 800 !important;
        }

        /* ---------------- PICKUP CODE ---------------- */

        .fl-code-box {
            display: flex;
            gap: 8px;
            justify-content: center;
            align-items: center;
            margin: 10px 0 14px;
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
        }

        /* ---------------- CHECKBOX ---------------- */

        div[data-testid="stCheckbox"] label {
            color: #1F1B2D !important;
        }

        /* ---------------- FOOTER ---------------- */

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# NAVIGATION
# ============================================================

def navbar(brand: str = "FoodLoop"):
    """Render top brand identity above navigation.

    The HTML is deliberately written on unindented single lines:
    Markdown treats 4+ leading spaces as a code block, which would
    print the raw HTML instead of rendering it.
    """

    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;padding:0.5rem 0 0.75rem 0;">'
        '<span style="display:inline-block;width:14px;height:14px;'
        'background-color:#F26B1D;border-radius:50%;"></span>'
        f'<span style="font-size:1.6rem;font-weight:800;color:#1F1B2D;'
        f'letter-spacing:-0.5px;">{brand}</span>'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# HERO SECTION
# ============================================================

def hero(headline: str, highlight_word: str, subtitle: str = ""):
    """Render large hero headline."""

    sub_html = (
        f"<p style='font-size:1.15rem; color:#6B7280; "
        f"font-weight:500; margin-top:0.5rem; line-height:1.5;'>"
        f"{subtitle}</p>"
        if subtitle else ""
    )

    st.markdown(_flat(f"""
        <div style="margin:0.75rem 0 1.25rem 0;">
            <h1 class="fl-hero-title">
                {headline}
                <span class="fl-highlight">{highlight_word}</span>
            </h1>
            {sub_html}
        </div>
        """), unsafe_allow_html=True)


# ============================================================
# IMPACT PILL
# ============================================================

def impact_pill(portions: int, co2_kg: float):
    """Show food-saving and CO2 impact metrics."""

    st.markdown(_flat(f"""
        <div style="
            display:inline-flex;
            align-items:center;
            gap:10px;
            background:#FFFFFF;
            border:1px solid #FFE8D6;
            box-shadow:0 2px 10px rgba(31,27,45,0.05);
            border-radius:9999px;
            padding:7px 18px;
            margin:0.4rem 0 1.25rem 0;
            font-size:0.9rem;
            color:#4B5563;
            font-weight:600;
        ">
            <span>🌱 <b>{portions}</b> portions saved</span>
            <span style="color:#CBD5E1;">&bull;</span>
            <span>💨 <b>{co2_kg} kg</b> CO₂ avoided</span>
        </div>
        """), unsafe_allow_html=True)


# ============================================================
# CATEGORY TILES
# ============================================================

def category_tiles() -> str:
    """Display category selection tiles."""

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

        if cols[i].button(
            btn_label,
            key=f"cat_tile_{name}",
            width="stretch",
            type=btn_type,
        ):
            st.session_state["selected_category"] = name
            st.rerun()

    return st.session_state.get("selected_category", "All")


# ============================================================
# FOOD IMAGES
# ============================================================
#
# Each item shows a REAL photo of that dish.
#
#   1. If  food_images/<item>.jpg|png|webp  exists next to ui.py it is
#      used. Put your own photo there any time and it wins.
#   2. Otherwise the photo is downloaded ONCE from Wikipedia (the lead
#      photo of the dish's article), saved into  food_images/  and reused
#      from then on, so it is fast and works offline afterwards.
#   3. If nothing can be found, a matching emoji is shown. Never a photo
#      of a different dish.

import base64
import mimetypes
import re
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

IMAGE_DIR = Path(__file__).parent / "food_images"
_HEADERS = {"User-Agent": "FoodLoop/1.0 (campus food-waste project)"}
_FAILED = set()  # items we could not download this run (avoid retry loops)

# name (lowercase) -> (Wikipedia article titles to try, emoji)
FOOD_LOOKS = {
    "idli": (["Idli"], "🥞"),
    "masala dosa": (["Masala_dosa", "Dosa"], "🥞"),
    "dosa": (["Dosa"], "🥞"),
    "upma": (["Upma"], "🍲"),
    "poha": (["Poha", "Poha_(food)"], "🍚"),
    "puri bhaji": (["Puri_(food)", "Poori"], "🫓"),
    "paratha": (["Paratha"], "🫓"),
    "sandwich": (["Sandwich"], "🥪"),
    "veg thali": (["Thali"], "🍛"),
    "south indian meals": (["Thali"], "🍛"),
    "north indian meals": (["Thali"], "🍛"),
    "veg biryani": (["Biryani"], "🍛"),
    "biryani": (["Biryani"], "🍛"),
    "paneer rice": (["Paneer"], "🍚"),
    "fried rice": (["Fried_rice"], "🍚"),
    "dal khichdi": (["Khichdi"], "🍲"),
    "samosa": (["Samosa"], "🥟"),
    "veg puff": (["Puff_pastry"], "🥐"),
    "puff": (["Puff_pastry"], "🥐"),
    "paneer roll": (["Kati_roll"], "🌯"),
    "roll": (["Kati_roll"], "🌯"),
    "vada pav": (["Vada_pav"], "🍔"),
    "pav bhaji": (["Pav_bhaji"], "🍛"),
    "french fries": (["French_fries"], "🍟"),
    "burger": (["Hamburger"], "🍔"),
    "pizza": (["Pizza"], "🍕"),
    "noodles": (["Noodle"], "🍜"),
    "tea": (["Tea"], "🍵"),
    "coffee": (["Coffee"], "☕"),
    "fresh juice": (["Juice"], "🧃"),
    "juice": (["Juice"], "🧃"),
    "lassi": (["Lassi"], "🥛"),
    "milkshake": (["Milkshake"], "🥤"),
    "gulab jamun": (["Gulab_jamun"], "🍮"),
    "cake": (["Cake"], "🍰"),
    "ice cream": (["Ice_cream"], "🍨"),
    "halwa": (["Halva"], "🍮"),
    "meal": (["Thali"], "🍛"),
    "rice": (["Cooked_rice", "Rice"], "🍚"),
}


def _norm(name) -> str:
    return " ".join(re.sub(r"\(.*?\)", " ", str(name or "")).lower().split())


def _slug(text) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def _look(name):
    """Return (key, wikipedia titles, emoji) for a food name."""
    n = _norm(name)
    if n in FOOD_LOOKS:
        titles, emoji = FOOD_LOOKS[n]
        return n, titles, emoji
    for key in sorted(FOOD_LOOKS, key=len, reverse=True):  # longest first
        if key in n:
            titles, emoji = FOOD_LOOKS[key]
            return key, titles, emoji
    # Unknown / custom item: try its own name as a Wikipedia title.
    title = "_".join(w.capitalize() for w in re.sub(r"[^a-z ]", "", n).split())
    return n, ([title] if title else []), "🍽️"


def food_emoji(name) -> str:
    return _look(name)[2]


def _find_local(*slugs):
    for slug in slugs:
        for ext in ("jpg", "jpeg", "png", "webp"):
            candidate = IMAGE_DIR / f"{slug}.{ext}"
            if candidate.is_file():
                return candidate
    return None


def _download_photo(titles, target: Path) -> bool:
    """Fetch the lead photo of the first matching Wikipedia article."""
    if requests is None:
        return False
    for title in titles:
        try:
            api = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
            meta = requests.get(api, headers=_HEADERS, timeout=6)
            if meta.status_code != 200:
                continue
            thumb = (meta.json().get("thumbnail") or {}).get("source")
            if not thumb:
                continue
            # Ask for a 500px wide version (a standard Wikimedia size).
            sized = re.sub(r"/\d+px-", "/500px-", thumb)
            for url in (sized, thumb):
                img = requests.get(url, headers=_HEADERS, timeout=10)
                ctype = img.headers.get("content-type", "")
                if img.status_code == 200 and ctype.startswith("image/") and img.content:
                    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(img.content)
                    return True
        except Exception:
            continue
    return False


def _photo_path(name):
    """Local photo for this item, downloading it the first time."""
    key, titles, _ = _look(name)
    slug = _slug(key)
    local = _find_local(_slug(_norm(name)), slug)
    if local:
        return local
    if not titles or slug in _FAILED:
        return None
    if _download_photo(titles, IMAGE_DIR / f"{slug}.jpg"):
        return IMAGE_DIR / f"{slug}.jpg"
    _FAILED.add(slug)
    return None


def food_image_src(name):
    """Data-URI of the dish photo for an HTML <img>, or None."""
    path = _photo_path(name)
    if path is None:
        return None
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def food_image_url(name):
    """Image for st.image(): the photo file, or an emoji tile if none."""
    path = _photo_path(name)
    if path is not None:
        return str(path)
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='300' height='200'>"
        "<rect width='300' height='200' fill='#FFE8D6'/>"
        "<text x='50%' y='55%' font-size='90' text-anchor='middle' "
        f"dominant-baseline='middle'>{food_emoji(name)}</text></svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


# ============================================================
# DEAL CARD
# ============================================================

def deal_card(row):
    """Display a food deal card."""

    name = row.get("name", "Item")
    img_url = food_image_src(name)
    emoji = food_emoji(name)
    img_html = (
        f'<img src="{img_url}" alt="" loading="lazy" '
        'style="width:100%;height:100%;object-fit:cover;display:block;"/>'
        if img_url else ""
    )

    mrp = int(row.get("mrp", 0))
    price_now = int(row.get("price_now", 0))
    group_price = int(row.get("group_price", price_now))
    quantity = int(row.get("quantity", 0))
    minutes_left = int(row.get("minutes_left", 0))
    discount_pct = int(row.get("discount_%", 0))

    pts = price_now // core.POINTS_PER_RUPEES

    time_badge_class = (
        "fl-badge fl-badge-urgent"
        if minutes_left < 30
        else "fl-badge fl-badge-time"
    )

    st.markdown(_flat(f"""
        <div class="fl-card"
             style="padding:1rem; border-radius:24px; margin-bottom:0.75rem;">

            <div style="
                position:relative;
                border-radius:18px;
                overflow:hidden;
                height:180px;
                background:#FFE8D6;
                isolation:isolate;
            ">
                <div style="
                    position:absolute;
                    inset:0;
                    z-index:-1;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:4.5rem;
                ">{emoji}</div>

                {img_html}

                <span class="fl-badge fl-badge-discount"
                      style="position:absolute;top:10px;left:10px;">
                    -{discount_pct}%
                </span>

                <span class="{time_badge_class}"
                      style="position:absolute;top:10px;right:10px;">
                    ⏱ {minutes_left} min
                </span>
            </div>

            <div style="padding:0.85rem 0.25rem 0.25rem;">

                <div style="
                    font-size:1.15rem;
                    font-weight:800;
                    color:#1F1B2D;
                    margin-bottom:6px;
                ">
                    {name}
                </div>

                <div style="
                    display:flex;
                    align-items:baseline;
                    gap:8px;
                    margin-bottom:6px;
                ">
                    <span style="
                        font-size:1.4rem;
                        font-weight:800;
                        color:#F26B1D;
                    ">
                        ₹{price_now}
                    </span>

                    <span style="
                        font-size:0.95rem;
                        color:#9CA3AF;
                        text-decoration:line-through;
                    ">
                        ₹{mrp}
                    </span>

                    <span style="
                        font-size:0.85rem;
                        font-weight:700;
                        color:#6B7280;
                        margin-left:auto;
                    ">
                        {quantity} left
                    </span>
                </div>

                <div style="
                    font-size:0.85rem;
                    color:#4B5563;
                    margin-bottom:8px;
                ">
                    Group deal:
                    <b>₹{group_price}</b>
                    ({core.GROUP_MIN_QTY}+ portions)
                </div>

                <span class="fl-badge fl-badge-points">
                    ⭐ earn {pts} pts
                </span>

            </div>
        </div>
        """), unsafe_allow_html=True)


# ============================================================
# PROMOTIONAL BANNER
# ============================================================

def promo_banner(title: str, subtitle: str = ""):
    """Display an orange promotional banner."""

    sub_html = (
        f"<p style='color:#FFFFFF;font-size:1.05rem;"
        f"margin:0;font-weight:500;'>{subtitle}</p>"
        if subtitle else ""
    )

    st.markdown(_flat(f"""
        <div style="
            background:linear-gradient(135deg,#F26B1D 0%,#FF8A3D 100%);
            border-radius:24px;
            padding:1.75rem 2rem;
            color:#FFFFFF;
            margin:2rem 0;
            box-shadow:0 8px 24px rgba(242,107,29,0.25);
        ">
            <h3 style="
                color:#FFFFFF !important;
                font-size:1.45rem;
                font-weight:800;
                margin:0 0 0.35rem;
            ">
                {title}
            </h3>

            {sub_html}
        </div>
        """), unsafe_allow_html=True)


# ============================================================
# PICKUP CARD
# ============================================================

def pickup_card(order):
    """Display order details, pickup code and QR code."""

    oid = int(order.get("order_id", 0))
    item = order.get("item_name", "Food Order")

    qty = order.get("qty")
    qty_str = f" &times; {int(qty)}" if qty else ""

    code = str(order.get("pickup_code", "")).zfill(6)

    digits_html = "".join(
        f"<div class='fl-code-digit'>{d}</div>"
        for d in code
    )

    st.markdown(_flat(f"""
        <div class="fl-card"
             style="
                text-align:center;
                max-width:440px;
                margin:1rem auto 0;
                padding:1.5rem 1.25rem 1rem;
             ">

            <div style="
                font-size:0.85rem;
                font-weight:700;
                color:#F26B1D;
                text-transform:uppercase;
            ">
                Pickup Pass
            </div>

            <div style="
                font-size:1.35rem;
                font-weight:800;
                color:#1F1B2D;
                margin:4px 0 2px;
            ">
                Order #{oid}
            </div>

            <div style="
                font-size:1.05rem;
                font-weight:600;
                color:#4B5563;
                margin-bottom:10px;
            ">
                {item}{qty_str}
            </div>

            <div class="fl-code-box">
                {digits_html}
            </div>

            <div style="
                font-size:0.85rem;
                color:#6B7280;
                margin-bottom:8px;
            ">
                Show this code or scan QR at the counter
            </div>

        </div>
        """), unsafe_allow_html=True)

    if qrcode is not None:

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )

        qr.add_data(code)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="#1F1B2D",
            back_color="#FFFFFF",
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        c1, c2, c3 = st.columns([1, 1, 1])

        with c2:
            st.image(buf, width=160)


# ============================================================
# ORDER STATUS BADGE
# ============================================================

def status_badge(status: str) -> str:
    """Return an HTML badge based on order status."""

    s = str(status)

    if s == "Pending":
        return _flat("""
        <span style="
            background-color:#FEF3C7;
            color:#92400E;
            border:1px solid #FCD34D;
            padding:4px 12px;
            border-radius:9999px;
            font-weight:700;
            font-size:0.82rem;
        ">Pending</span>
        """)

    elif s == "Collected":
        return _flat("""
        <span style="
            background-color:#E8F8F1;
            color:#1FA971;
            border:1px solid #A7F3D0;
            padding:4px 12px;
            border-radius:9999px;
            font-weight:700;
            font-size:0.82rem;
        ">Collected</span>
        """)

    else:
        return _flat("""
        <span style="
            background-color:#F3F4F6;
            color:#6B7280;
            border:1px solid #E5E7EB;
            padding:4px 12px;
            border-radius:9999px;
            font-weight:700;
            font-size:0.82rem;
        ">Cancelled</span>
        """)


# ============================================================
# FOOTER
# ============================================================

def footer():
    """Display the FoodLoop footer."""

    st.markdown(_flat("""
        <div style="
            text-align:center;
            color:#9CA3AF;
            font-size:0.85rem;
            font-weight:500;
            border-top:1px solid #FFE8D6;
            padding:1.75rem 0 1.25rem;
            margin-top:3rem;
        ">
            FoodLoop &bull; Samsung Innovation Lab
        </div>
        """), unsafe_allow_html=True)