# ♻️ FoodLoop

A Streamlit + pandas web app that helps canteens sell surplus food at time-based discounts, rewarding students with points and cutting waste.

## Features
- **Live Food Saved Counter** (portions, kg, CO₂ avoided) on the home page
- **Dynamic discounts**: 15% (3h) → 25% (2h) → 40% (1h) → 50% (30 min)
- **Group deals**: 5+ portions get an extra 15% off
- **FoodLoop Wallet**: points balance, earned/redeemed, full history, redeem at checkout
- **Referral rewards**: 20 points each after the friend's first purchase
- **Waste forecast**: suggests how much less to cook, based on past same-weekday sales
- Student and canteen (vendor) roles

## Run
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Demo logins: `student@foodloop.com / student123`, `canteen@foodloop.com / vendor123`.
Data is stored as CSVs in `data/` (auto-created with demo data).

## Structure
- `app.py` – Streamlit UI
- `core.py` – pricing, wallet, referral, forecasting, storage

## Roadmap
SQLite/Postgres, bcrypt passwords, payments (UPI), QR pickup, ML-based forecasting.
