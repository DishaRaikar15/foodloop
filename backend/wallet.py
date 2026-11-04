from backend.database import get_connection


def get_wallet_balance(user_id):
    """Return the signed sum of a user's wallet transactions."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(points), 0) AS balance "
            "FROM wallet_transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["balance"] or 0)
    finally:
        conn.close()


def earn_points(user_id, order_id):
    """Award 1 point per ₹10 on a collected order, at most once."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = conn.execute(
            "SELECT user_id, total_paid, status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not order or order["user_id"] != user_id:
            conn.rollback()
            return False, "Order not found."
        if order["status"] != "collected":
            conn.rollback()
            return False, "Points are awarded only after food collection."

        existing = conn.execute(
            "SELECT 1 FROM wallet_transactions "
            "WHERE user_id = ? AND order_id = ? AND kind = 'earned' "
            "AND note = ? LIMIT 1",
            (user_id, order_id, "Points earned from collected order"),
        ).fetchone()
        if existing:
            conn.rollback()
            return False, "Points have already been awarded for this order."

        points = max(0, int(float(order["total_paid"]) // 10))
        if points == 0:
            conn.rollback()
            return False, "This order does not qualify for reward points."

        conn.execute(
            "INSERT INTO wallet_transactions "
            "(user_id, kind, points, note, order_id) "
            "VALUES (?, 'earned', ?, ?, ?)",
            (user_id, points, "Points earned from collected order", order_id),
        )
        conn.commit()
        return True, f"{points} reward points earned!"
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def redeem_points(user_id, order_id, points_to_use):
    """Redeem wallet points once on a placed order, subject to 50% cap."""
    try:
        if isinstance(points_to_use, bool):
            raise ValueError
        points_to_use = int(points_to_use)
        if points_to_use <= 0:
            return False, "Enter a valid number of points."
    except (ValueError, TypeError, OverflowError):
        return False, "Invalid points amount."

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = conn.execute(
            "SELECT user_id, total_paid, status, points_used "
            "FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not order or order["user_id"] != user_id:
            conn.rollback()
            return False, "Order not found."
        if order["status"] != "placed":
            conn.rollback()
            return False, "Only active orders can use wallet points."
        if int(order["points_used"] or 0) > 0:
            conn.rollback()
            return False, "Points have already been applied to this order."

        balance = conn.execute(
            "SELECT COALESCE(SUM(points), 0) AS balance "
            "FROM wallet_transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()["balance"]
        if balance < 0 or points_to_use > balance:
            conn.rollback()
            return False, "Insufficient wallet balance."

        maximum_allowed = int(float(order["total_paid"]) * 0.5)
        if points_to_use > maximum_allowed:
            conn.rollback()
            return False, "You can redeem points for only 50% of the bill."

        new_total = round(float(order["total_paid"]) - points_to_use, 2)
        updated = conn.execute(
            "UPDATE orders SET points_used = ?, total_paid = ? "
            "WHERE order_id = ? AND user_id = ? AND status = 'placed' "
            "AND COALESCE(points_used, 0) = 0",
            (points_to_use, new_total, order_id, user_id),
        )
        if updated.rowcount != 1:
            conn.rollback()
            return False, "Order changed. Please try again."

        conn.execute(
            "INSERT INTO wallet_transactions "
            "(user_id, kind, points, note, order_id) "
            "VALUES (?, 'redeemed', ?, ?, ?)",
            (user_id, -points_to_use, "Points redeemed for food order", order_id),
        )
        conn.commit()
        return True, f"{points_to_use} points redeemed successfully!"
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_wallet_history(user_id):
    """Return a user's wallet transactions, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT transaction_id, kind, points, note, order_id, created_at "
            "FROM wallet_transactions WHERE user_id = ? "
            "ORDER BY transaction_id DESC",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
