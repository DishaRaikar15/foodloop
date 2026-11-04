
from backend.database import get_connection


# Project assumptions for impact estimation
WEIGHT_PER_PORTION_KG = 0.4
CO2_SAVED_PER_KG = 2.5


def get_foodloop_impact():
    """Calculate total FoodLoop environmental impact."""

    conn = get_connection()

    try:
        result = conn.execute(
            """
            SELECT
                COALESCE(SUM(qty), 0) AS total_portions,
                COUNT(*) AS total_orders,
                COALESCE(SUM(total_paid), 0) AS total_revenue
            FROM orders
            WHERE status = 'collected'
            """
        ).fetchone()

        portions = result["total_portions"]

        food_rescued = portions * WEIGHT_PER_PORTION_KG

        co2_saved = food_rescued * CO2_SAVED_PER_KG

        return {
            "total_portions": portions,
            "total_orders": result["total_orders"],
            "total_revenue": round(result["total_revenue"], 2),
            "food_rescued_kg": round(food_rescued, 2),
            "co2_saved_kg": round(co2_saved, 2)
        }

    finally:
        conn.close()


def get_vendor_impact(vendor_id):
    """Calculate the environmental impact created by one vendor."""

    conn = get_connection()

    try:
        result = conn.execute(
            """
            SELECT
                COALESCE(SUM(o.qty), 0) AS total_portions,
                COUNT(o.order_id) AS total_orders,
                COALESCE(SUM(o.total_paid), 0) AS total_revenue
            FROM orders o
            JOIN food_items f ON o.item_id = f.item_id
            WHERE f.vendor_id = ?
              AND o.status = 'collected'
            """,
            (vendor_id,)
        ).fetchone()

        portions = result["total_portions"]

        food_rescued = portions * WEIGHT_PER_PORTION_KG

        co2_saved = food_rescued * CO2_SAVED_PER_KG

        return {
            "total_portions": portions,
            "total_orders": result["total_orders"],
            "total_revenue": round(result["total_revenue"], 2),
            "food_rescued_kg": round(food_rescued, 2),
            "co2_saved_kg": round(co2_saved, 2)
        }

    finally:
        conn.close()
