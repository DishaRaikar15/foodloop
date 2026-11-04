
from datetime import datetime, date

from backend.database import get_connection


def record_food_history(vendor_id, item, prepared, sold, record_date=None):
    """Store daily food preparation and sales history."""

    item = item.strip()

    if not item:
        return False, "Food item name is required."

    try:
        prepared = int(prepared)
        sold = int(sold)

        if prepared <= 0:
            return False, "Prepared quantity must be positive."

        if sold < 0 or sold > prepared:
            return False, "Sold quantity must be between 0 and prepared quantity."

        if record_date is None:
            record_date = date.today().isoformat()

        parsed_date = date.fromisoformat(record_date)
        weekday = parsed_date.strftime("%A")

    except (ValueError, TypeError):
        return False, "Please enter valid date and quantities."

    conn = get_connection()

    try:
        vendor = conn.execute(
            "SELECT user_id FROM users WHERE user_id = ? AND role = 'vendor'",
            (vendor_id,)
        ).fetchone()

        if not vendor:
            return False, "Vendor account not found."

        conn.execute(
            """
            INSERT INTO food_history
            (date, weekday, item, prepared, sold, vendor_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record_date,
                weekday,
                item,
                prepared,
                sold,
                vendor_id
            )
        )

        conn.commit()

        return True, "Food history recorded successfully!"

    finally:
        conn.close()


def predict_food_demand(vendor_id, item, prepared_quantity, target_date=None):
    """Predict demand using historical sales for the same weekday."""

    item = item.strip()

    try:
        prepared_quantity = int(prepared_quantity)

        if not item:
            raise ValueError("Food item name is required.")

        if prepared_quantity <= 0:
            raise ValueError("Prepared quantity must be positive.")

        if target_date is None:
            target_date = date.today().isoformat()

        parsed_date = date.fromisoformat(target_date)
        weekday = parsed_date.strftime("%A")

    except (ValueError, TypeError):
        raise ValueError("Please enter valid item, date and quantity.")

    conn = get_connection()

    try:
        history = conn.execute(
            """
            SELECT sold
            FROM food_history
            WHERE vendor_id = ?
              AND LOWER(item) = LOWER(?)
              AND weekday = ?
              AND date < ?
            ORDER BY date DESC
            LIMIT 8
            """,
            (vendor_id, item, weekday, target_date)
        ).fetchall()

        if not history:
            return {
                "item": item,
                "weekday": weekday,
                "prepared_quantity": prepared_quantity,
                "predicted_demand": None,
                "expected_surplus": None,
                "message": "Not enough historical data. Record previous sales first."
            }

        sales = [row["sold"] for row in history]

        predicted_demand = round(sum(sales) / len(sales))

        expected_surplus = max(
            0,
            prepared_quantity - predicted_demand
        )

        return {
            "item": item,
            "weekday": weekday,
            "prepared_quantity": prepared_quantity,
            "predicted_demand": predicted_demand,
            "expected_surplus": expected_surplus,
            "historical_records_used": len(sales),
            "message": "Demand prediction generated successfully."
        }

    finally:
        conn.close()
