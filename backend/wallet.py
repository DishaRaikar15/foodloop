
from backend.database import get_connection


def get_wallet_balance(user_id):
    """Calculate a student's current wallet balance."""

    conn = get_connection()

    try:
        result = conn.execute(
            """
            SELECT COALESCE(SUM(points), 0) AS balance
            FROM wallet_transactions
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        return result["balance"]

    finally:
        conn.close()


def earn_points(user_id, order_id):
    """Award 1 point for every Rs. 10 spent on a collected order."""

    conn = get_connection()

    try:
        order = conn.execute(
            """
            SELECT user_id, total_paid, status
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,)
        ).fetchone()

        if not order or order["user_id"] != user_id:
            return False, "Order not found."

        if order["status"] != "collected":
            return False, "Points are awarded only after food collection."

        existing = conn.execute(
            """
            SELECT transaction_id
            FROM wallet_transactions
            WHERE order_id = ? AND kind = 'earned'
            """,
            (order_id,)
        ).fetchone()

        if existing:
            return False, "Points have already been awarded for this order."

        points = int(order["total_paid"] // 10)

        if points <= 0:
            return False, "This order does not qualify for reward points."

        conn.execute(
            """
            INSERT INTO wallet_transactions
            (user_id, kind, points, note, order_id)
            VALUES (?, 'earned', ?, ?, ?)
            """,
            (
                user_id,
                points,
                "Points earned from collected order",
                order_id
            )
        )

        conn.commit()

        return True, f"{points} reward points earned!"

    finally:
        conn.close()


def redeem_points(user_id, order_id, points_to_use):
    """Redeem wallet points with a maximum 50% bill limit."""

    try:
        points_to_use = int(points_to_use)

        if points_to_use <= 0:
            return False, "Enter a valid number of points."

    except (ValueError, TypeError):
        return False, "Invalid points amount."

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        order = conn.execute(
            """
            SELECT user_id, total_paid, status, points_used
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,)
        ).fetchone()

        if not order or order["user_id"] != user_id:
            return False, "Order not found."

        if order["status"] != "placed":
            return False, "Only active orders can use wallet points."

        if order["points_used"] > 0:
            return False, "Points have already been applied to this order."

        balance_result = conn.execute(
            """
            SELECT COALESCE(SUM(points), 0) AS balance
            FROM wallet_transactions
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        balance = balance_result["balance"]

        maximum_allowed = int(order["total_paid"] * 0.5)

        if points_to_use > balance:
            return False, "Insufficient wallet balance."

        if points_to_use > maximum_allowed:
            return False, "You can redeem points for only 50% of the bill."

        new_total = round(order["total_paid"] - points_to_use, 2)

        conn.execute(
            """
            UPDATE orders
            SET points_used = ?, total_paid = ?
            WHERE order_id = ?
            """,
            (points_to_use, new_total, order_id)
        )

        conn.execute(
            """
            INSERT INTO wallet_transactions
            (user_id, kind, points, note, order_id)
            VALUES (?, 'redeemed', ?, ?, ?)
            """,
            (
                user_id,
                -points_to_use,
                "Points redeemed for food order",
                order_id
            )
        )

        conn.commit()

        return True, f"{points_to_use} points redeemed successfully!"

    finally:
        conn.close()


def get_wallet_history(user_id):
    """Display all wallet transactions."""

    conn = get_connection()

    try:
        transactions = conn.execute(
            """
            SELECT transaction_id, kind, points, note,
                   order_id, created_at
            FROM wallet_transactions
            WHERE user_id = ?
            ORDER BY transaction_id DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(transaction) for transaction in transactions]

    finally:
        conn.close()
