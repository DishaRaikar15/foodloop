
from datetime import datetime

from backend.database import get_connection
from backend.pricing import calculate_price
from backend.security import (
    generate_pickup_code,
    encrypt_pickup_code,
    decrypt_pickup_code,
    hash_pickup_code,
    verify_pickup_code
)


def place_order(user_id, item_id, quantity, points_to_use=0):
    """
    Place an order, deduct stock and optionally redeem wallet points.
    Order creation and wallet redemption happen in one transaction.
    """

    try:
        quantity = int(quantity)
        points_to_use = int(points_to_use)

        if quantity <= 0:
            return None, "Quantity must be at least 1."

        if points_to_use < 0:
            return None, "Wallet points cannot be negative."

    except (ValueError, TypeError):
        return None, "Please enter valid quantity and wallet points."

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        student = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = ? AND role = 'student'
            """,
            (user_id,)
        ).fetchone()

        if not student:
            conn.rollback()
            return None, "Only registered students can place orders."

        item = conn.execute(
            """
            SELECT item_id, vendor_id, name, mrp, quantity,
                   expires_at, is_active
            FROM food_items
            WHERE item_id = ?
            """,
            (item_id,)
        ).fetchone()

        if not item:
            conn.rollback()
            return None, "Food item not found."

        if item["is_active"] != 1:
            conn.rollback()
            return None, "This food item is no longer available."

        if item["expires_at"] <= datetime.now().strftime("%Y-%m-%d %H:%M"):
            conn.rollback()
            return None, "This food item has expired."

        if item["quantity"] < quantity:
            conn.rollback()
            return None, "Not enough portions available."

        # Calculate expiry and group discounts.
        price = calculate_price(
            item["mrp"],
            item["expires_at"],
            quantity
        )

        gross_total = round(price["total_price"], 2)

        # Maximum wallet redemption is 50% of the discounted bill.
        maximum_points = int(gross_total * 0.50)

        if points_to_use > maximum_points:
            conn.rollback()
            return None, (
                f"You can redeem a maximum of {maximum_points} "
                "points for this order."
            )

        # Check the student's wallet balance.
        wallet = conn.execute(
            """
            SELECT COALESCE(SUM(points), 0) AS balance
            FROM wallet_transactions
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        wallet_balance = wallet["balance"]

        if points_to_use > wallet_balance:
            conn.rollback()
            return None, "Insufficient wallet points."

        # Generate a secure six-digit pickup code.
        pickup_code = generate_pickup_code()

        # Insert the order first to obtain its order ID.
        cursor = conn.execute(
            """
            INSERT INTO orders
            (
                user_id, item_id, item_name, qty, unit_price,
                points_used, total_paid, group_deal, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'placed')
            """,
            (
                user_id,
                item_id,
                item["name"],
                quantity,
                price["final_unit_price"],
                points_to_use,
                round(gross_total - points_to_use, 2),
                1 if quantity >= 5 else 0
            )
        )

        order_id = cursor.lastrowid

        # Store the verification hash and encrypted pickup code.
        code_hash = hash_pickup_code(order_id, pickup_code)
        encrypted_code = encrypt_pickup_code(pickup_code)

        conn.execute(
            """
            UPDATE orders
            SET pickup_code_hash = ?,
                pickup_code_encrypted = ?
            WHERE order_id = ?
            """,
            (code_hash, encrypted_code, order_id)
        )

        # Deduct wallet points in the same transaction.
        if points_to_use > 0:
            conn.execute(
                """
                INSERT INTO wallet_transactions
                (user_id, kind, points, note, order_id)
                VALUES (?, 'redeemed', ?, ?, ?)
                """,
                (
                    user_id,
                    -points_to_use,
                    "Points redeemed during checkout",
                    order_id
                )
            )

        # Reduce available food stock.
        stock_update = conn.execute(
            """
            UPDATE food_items
            SET quantity = quantity - ?
            WHERE item_id = ?
              AND quantity >= ?
              AND is_active = 1
            """,
            (quantity, item_id, quantity)
        )

        if stock_update.rowcount != 1:
            conn.rollback()
            return None, "Food stock changed. Please try again."

        conn.commit()

        return {
            "order_id": order_id,
            "item_id": item_id,
            "item_name": item["name"],
            "quantity": quantity,
            "mrp": item["mrp"],
            "unit_price": price["final_unit_price"],
            "expiry_discount": price["expiry_discount"],
            "group_discount": price["group_discount"],
            "gross_total": gross_total,
            "points_used": points_to_use,
            "total_paid": round(gross_total - points_to_use, 2),
            "pickup_code": pickup_code,
            "status": "placed"
        }, "Order placed successfully!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_student_orders(user_id):
    """
    Get a student's orders.
    Return pickup codes only for pending orders.
    Never expose hashes or encrypted values.
    """

    conn = get_connection()

    try:
        student = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = ? AND role = 'student'
            """,
            (user_id,)
        ).fetchone()

        if not student:
            return []

        orders = conn.execute(
            """
            SELECT
                order_id,
                user_id,
                item_id,
                item_name,
                qty,
                unit_price,
                points_used,
                total_paid,
                group_deal,
                status,
                created_at,
                collected_at,
                pickup_code_encrypted
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC, order_id DESC
            """,
            (user_id,)
        ).fetchall()

        result = []

        for order in orders:
            order_data = dict(order)

            encrypted_code = order_data.pop(
                "pickup_code_encrypted", None
            )

            if order_data["status"] == "placed" and encrypted_code:
                order_data["pickup_code"] = decrypt_pickup_code(
                    encrypted_code
                )
            else:
                order_data["pickup_code"] = None

            result.append(order_data)

        return result

    finally:
        conn.close()


def get_student_pending_orders(user_id):
    """Get only pending orders and pickup codes for a student."""

    return [
        order
        for order in get_student_orders(user_id)
        if order["status"] == "placed"
    ]


def get_vendor_orders(vendor_id):
    """
    Get orders belonging to a vendor.
    Pickup codes and their protected values are excluded.
    """

    conn = get_connection()

    try:
        vendor = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = ? AND role = 'vendor'
            """,
            (vendor_id,)
        ).fetchone()

        if not vendor:
            return []

        orders = conn.execute(
            """
            SELECT
                o.order_id,
                o.user_id,
                o.item_id,
                o.item_name,
                o.qty,
                o.unit_price,
                o.points_used,
                o.total_paid,
                o.group_deal,
                o.status,
                o.created_at,
                o.collected_at,
                u.name AS student_name
            FROM orders o
            JOIN food_items f ON o.item_id = f.item_id
            JOIN users u ON o.user_id = u.user_id
            WHERE f.vendor_id = ?
            ORDER BY o.created_at DESC, o.order_id DESC
            """,
            (vendor_id,)
        ).fetchall()

        return [dict(order) for order in orders]

    finally:
        conn.close()


def mark_order_collected(vendor_id, order_id, pickup_code):
    """
    Verify pickup code and collect an order.
    Process wallet and referral rewards in the same transaction.
    """

    if not isinstance(pickup_code, str):
        return False, "Please enter a valid six-digit pickup code."

    pickup_code = pickup_code.strip()

    if len(pickup_code) != 6 or not pickup_code.isdigit():
        return False, "Pickup code must contain exactly six digits."

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        vendor = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = ? AND role = 'vendor'
            """,
            (vendor_id,)
        ).fetchone()

        if not vendor:
            conn.rollback()
            return False, "Invalid vendor account."

        order = conn.execute(
            """
            SELECT
                o.order_id,
                o.user_id,
                o.total_paid,
                o.status,
                o.pickup_code_hash,
                u.referred_by,
                u.first_purchase_done
            FROM orders o
            JOIN food_items f ON o.item_id = f.item_id
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = ?
              AND f.vendor_id = ?
            """,
            (order_id, vendor_id)
        ).fetchone()

        if not order:
            conn.rollback()
            return False, "Order not found or does not belong to you."

        if order["status"] == "cancelled":
            conn.rollback()
            return False, "This order has been cancelled."

        if order["status"] == "collected":
            conn.rollback()
            return False, "This order has already been collected."

        if order["status"] != "placed":
            conn.rollback()
            return False, "This order cannot be collected."

        # Verify the code belongs to this order.
        if not verify_pickup_code(
            order_id,
            pickup_code,
            order["pickup_code_hash"]
        ):
            conn.rollback()
            return False, "Incorrect pickup code."

        # Collect order and invalidate its pickup code.
        conn.execute(
            """
            UPDATE orders
            SET status = 'collected',
                collected_at = CURRENT_TIMESTAMP,
                pickup_code_hash = NULL,
                pickup_code_encrypted = NULL
            WHERE order_id = ?
              AND status = 'placed'
            """,
            (order_id,)
        )

        # Award normal wallet points.
        purchase_note = "Points earned from collected order"

        existing_reward = conn.execute(
            """
            SELECT transaction_id
            FROM wallet_transactions
            WHERE user_id = ?
              AND order_id = ?
              AND kind = 'earned'
              AND note = ?
            """,
            (order["user_id"], order_id, purchase_note)
        ).fetchone()

        if not existing_reward:
            earned_points = int(order["total_paid"] // 10)

            if earned_points > 0:
                conn.execute(
                    """
                    INSERT INTO wallet_transactions
                    (user_id, kind, points, note, order_id)
                    VALUES (?, 'earned', ?, ?, ?)
                    """,
                    (
                        order["user_id"],
                        earned_points,
                        purchase_note,
                        order_id
                    )
                )

        # Award first-collection referral rewards once.
        if not order["first_purchase_done"]:
            conn.execute(
                """
                UPDATE users
                SET first_purchase_done = 1
                WHERE user_id = ?
                  AND first_purchase_done = 0
                """,
                (order["user_id"],)
            )

            referrer_id = order["referred_by"]

            if referrer_id:
                referrer = conn.execute(
                    """
                    SELECT user_id
                    FROM users
                    WHERE user_id = ? AND role = 'student'
                    """,
                    (referrer_id,)
                ).fetchone()

                if referrer:
                    conn.execute(
                        """
                        INSERT INTO wallet_transactions
                        (user_id, kind, points, note, order_id)
                        VALUES (?, 'earned', 20, ?, ?)
                        """,
                        (
                            order["user_id"],
                            "First-purchase referral bonus",
                            order_id
                        )
                    )

                    conn.execute(
                        """
                        INSERT INTO wallet_transactions
                        (user_id, kind, points, note, order_id)
                        VALUES (?, 'earned', 20, ?, ?)
                        """,
                        (
                            referrer_id,
                            "Referral bonus for inviting a student",
                            order_id
                        )
                    )

        conn.commit()

        return True, (
            "Order collected successfully! "
            "Eligible wallet and referral rewards processed."
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def cancel_order(user_id, order_id):
    """
    Cancel a pending order, restore stock and refund redeemed points.
    All operations happen in one transaction.
    """

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        student = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = ? AND role = 'student'
            """,
            (user_id,)
        ).fetchone()

        if not student:
            conn.rollback()
            return False, "Only registered students can cancel orders."

        order = conn.execute(
            """
            SELECT item_id, qty, points_used
            FROM orders
            WHERE order_id = ?
              AND user_id = ?
              AND status = 'placed'
            """,
            (order_id, user_id)
        ).fetchone()

        if not order:
            conn.rollback()
            return False, "Order not found or cannot be cancelled."

        # Cancel order and invalidate pickup code.
        conn.execute(
            """
            UPDATE orders
            SET status = 'cancelled',
                pickup_code_hash = NULL,
                pickup_code_encrypted = NULL
            WHERE order_id = ?
              AND status = 'placed'
            """,
            (order_id,)
        )

        # Restore available food stock.
        conn.execute(
            """
            UPDATE food_items
            SET quantity = quantity + ?
            WHERE item_id = ?
            """,
            (order["qty"], order["item_id"])
        )

        # Refund redeemed points.
        if order["points_used"] > 0:
            conn.execute(
                """
                INSERT INTO wallet_transactions
                (user_id, kind, points, note, order_id)
                VALUES (?, 'refund', ?, ?, ?)
                """,
                (
                    user_id,
                    order["points_used"],
                    "Refund for cancelled order",
                    order_id
                )
            )

        conn.commit()

        return True, (
            "Order cancelled, stock restored and wallet points refunded!"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def place_cart_order(user_id, cart_items, points_to_use=0,
                     coupon_discount=0):
    """
    Place all cart items in one SQLite transaction.
    Each item receives its own order and secure pickup code.
    """

    try:
        points_to_use = int(points_to_use)
        coupon_discount = round(float(coupon_discount), 2)

        if not cart_items:
            return None, "Your cart is empty."

        if points_to_use < 0 or coupon_discount < 0:
            return None, "Invalid discount or wallet points."

        cleaned_cart = {}
        for item_id, quantity in cart_items.items():
            quantity = int(quantity)
            if quantity <= 0:
                return None, "Invalid item quantity."
            cleaned_cart[item_id] = quantity

    except (ValueError, TypeError, AttributeError):
        return None, "Invalid cart details."

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        student = conn.execute(
            "SELECT user_id FROM users "
            "WHERE user_id = ? AND role = 'student'",
            (user_id,)
        ).fetchone()

        if not student:
            conn.rollback()
            return None, "Only registered students can place orders."

        lines = []
        subtotal = 0.0

        for item_id, quantity in cleaned_cart.items():
            item = conn.execute(
                """
                SELECT item_id, name, mrp, quantity,
                       expires_at, is_active
                FROM food_items
                WHERE item_id = ?
                """,
                (item_id,)
            ).fetchone()

            if not item or item["is_active"] != 1:
                conn.rollback()
                return None, "One or more food items are unavailable."

            if item["expires_at"] <= datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            ):
                conn.rollback()
                return None, f"{item['name']} has expired."

            if item["quantity"] < quantity:
                conn.rollback()
                return None, f"Not enough portions of {item['name']}."

            price = calculate_price(
                item["mrp"], item["expires_at"], quantity
            )

            line_total = price["total_price"]
            subtotal += line_total

            lines.append({
                "item": item,
                "quantity": quantity,
                "price": price,
                "gross": line_total
            })

        subtotal = round(subtotal, 2)

        if coupon_discount > subtotal:
            conn.rollback()
            return None, "Invalid coupon discount."

        discounted_total = round(subtotal - coupon_discount, 2)

        maximum_points = int(discounted_total * 0.50)

        if points_to_use > maximum_points:
            conn.rollback()
            return None, (
                f"You can redeem a maximum of {maximum_points} points."
            )

        balance = conn.execute(
            """
            SELECT COALESCE(SUM(points), 0) AS balance
            FROM wallet_transactions
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()["balance"]

        if points_to_use > balance:
            conn.rollback()
            return None, "Insufficient wallet points."

        # Distribute coupon discount proportionally.
        remaining_coupon = coupon_discount
        remaining_points = points_to_use
        remaining_gross = subtotal

        results = []

        for index, line in enumerate(lines):
            is_last = index == len(lines) - 1

            if is_last:
                line_coupon = round(remaining_coupon, 2)
                line_points = remaining_points
            else:
                line_coupon = round(
                    coupon_discount * line["gross"] / subtotal, 2
                ) if subtotal else 0

                line_coupon = min(line_coupon, remaining_coupon)

                eligible = max(0, line["gross"] - line_coupon)

                line_points = int(
                    points_to_use * eligible / discounted_total
                ) if discounted_total else 0

                line_points = min(line_points, remaining_points)

            remaining_coupon = round(
                remaining_coupon - line_coupon, 2
            )
            remaining_points -= line_points
            remaining_gross -= line["gross"]

            net_amount = round(
                line["gross"] - line_coupon - line_points, 2
            )

            pickup_code = generate_pickup_code()

            item = line["item"]
            price = line["price"]
            quantity = line["quantity"]

            cursor = conn.execute(
                """
                INSERT INTO orders
                (
                    user_id, item_id, item_name, qty, unit_price,
                    points_used, total_paid, group_deal, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'placed')
                """,
                (
                    user_id,
                    item["item_id"],
                    item["name"],
                    quantity,
                    price["final_unit_price"],
                    line_points,
                    net_amount,
                    1 if quantity >= 5 else 0
                )
            )

            order_id = cursor.lastrowid

            conn.execute(
                """
                UPDATE orders
                SET pickup_code_hash = ?,
                    pickup_code_encrypted = ?
                WHERE order_id = ?
                """,
                (
                    hash_pickup_code(order_id, pickup_code),
                    encrypt_pickup_code(pickup_code),
                    order_id
                )
            )

            if line_points > 0:
                conn.execute(
                    """
                    INSERT INTO wallet_transactions
                    (user_id, kind, points, note, order_id)
                    VALUES (?, 'redeemed', ?, ?, ?)
                    """,
                    (
                        user_id,
                        -line_points,
                        "Points redeemed during cart checkout",
                        order_id
                    )
                )

            stock_update = conn.execute(
                """
                UPDATE food_items
                SET quantity = quantity - ?
                WHERE item_id = ?
                  AND quantity >= ?
                  AND is_active = 1
                """,
                (quantity, item["item_id"], quantity)
            )

            if stock_update.rowcount != 1:
                conn.rollback()
                return None, "Food stock changed. Please try again."

            results.append({
                "order_id": order_id,
                "item_id": item["item_id"],
                "item_name": item["name"],
                "qty": quantity,
                "quantity": quantity,
                "pickup_code": pickup_code,
                "points_used": line_points,
                "total_paid": net_amount,
                "status": "placed"
            })

        conn.commit()
        return results, "Cart order placed successfully!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def cancel_vendor_order(vendor_id, order_id):
    """Allow a vendor to cancel their own pending order."""

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        vendor = conn.execute(
            """
            SELECT user_id FROM users
            WHERE user_id = ? AND role = 'vendor'
            """,
            (vendor_id,)
        ).fetchone()

        if not vendor:
            conn.rollback()
            return False, "Invalid vendor account."

        order = conn.execute(
            """
            SELECT o.item_id, o.qty, o.points_used
            FROM orders o
            JOIN food_items f ON o.item_id = f.item_id
            WHERE o.order_id = ?
              AND f.vendor_id = ?
              AND o.status = 'placed'
            """,
            (order_id, vendor_id)
        ).fetchone()

        if not order:
            conn.rollback()
            return False, "Order not found or cannot be cancelled."

        conn.execute(
            """
            UPDATE orders
            SET status = 'cancelled',
                pickup_code_hash = NULL,
                pickup_code_encrypted = NULL
            WHERE order_id = ?
              AND status = 'placed'
            """,
            (order_id,)
        )

        conn.execute(
            """
            UPDATE food_items
            SET quantity = quantity + ?
            WHERE item_id = ?
            """,
            (order["qty"], order["item_id"])
        )

        if order["points_used"] > 0:
            conn.execute(
                """
                INSERT INTO wallet_transactions
                (user_id, kind, points, note, order_id)
                SELECT user_id, 'refund', ?, ?, ?
                FROM orders
                WHERE order_id = ?
                """,
                (
                    order["points_used"],
                    "Refund for vendor-cancelled order",
                    order_id,
                    order_id
                )
            )

        conn.commit()
        return True, "Order cancelled and stock and wallet points restored!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
