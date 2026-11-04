"""
Referral reward compatibility module.

Referral rewards are handled automatically by
backend.order.mark_order_collected().

This function only verifies that the rewards were recorded.
It does not issue additional points.
"""

from backend.database import get_connection


def award_referral_bonus(student_id, order_id):
    """
    Verify that referral bonuses were awarded during collection.

    Referral rewards must be issued only once, by
    mark_order_collected().
    """
    conn = get_connection()

    try:
        order = conn.execute(
            """
            SELECT user_id, status
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,)
        ).fetchone()

        if not order:
            return False, "Order not found."

        if order["user_id"] != student_id:
            return False, "Order does not belong to this student."

        if order["status"] != "collected":
            return False, "Order has not been collected."

        transactions = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM wallet_transactions
            WHERE order_id = ?
              AND note LIKE '%Referral bonus%'
            """,
            (order_id,)
        ).fetchone()

        if transactions["total"] >= 2:
            return True, "Referral bonuses were already awarded during collection."

        return False, (
            "No complete referral reward record was found. "
            "Referral rewards are handled during order collection."
        )

    finally:
        conn.close()
