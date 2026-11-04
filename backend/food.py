
from datetime import datetime
import math
from urllib.parse import urlparse

from backend.database import get_connection
from backend.pricing import calculate_price


def _validate_food_details(name, mrp, quantity, expires_at,
                           category="Other", image_url=None):
    """Validate food listing information."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Food name is required.")

    if not isinstance(category, str) or not category.strip():
        raise ValueError("Food category is required.")

    try:
        mrp = float(mrp)
        quantity = int(quantity)

        if not math.isfinite(mrp) or mrp <= 0:
            raise ValueError("Price must be greater than zero.")

        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")

        expiry = datetime.strptime(
            expires_at, "%Y-%m-%d %H:%M"
        )

        if expiry <= datetime.now():
            raise ValueError("Expiry time must be in the future.")

    except (ValueError, TypeError):
        raise ValueError(
            "Please enter valid price, quantity and expiry time."
        )

    if image_url:
        if not isinstance(image_url, str):
            raise ValueError("Invalid image URL.")

        image_url = image_url.strip()
        parsed_url = urlparse(image_url)

        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            raise ValueError("Image URL must be a valid HTTP or HTTPS URL.")

    return (
        name.strip(),
        mrp,
        quantity,
        expiry.strftime("%Y-%m-%d %H:%M"),
        category.strip(),
        image_url or None
    )


def _is_vendor(conn, vendor_id):
    """Check whether the supplied account is a registered vendor."""

    return conn.execute(
        """
        SELECT user_id
        FROM users
        WHERE user_id = ? AND role = 'vendor'
        """,
        (vendor_id,)
    ).fetchone() is not None


def _format_food_item(item):
    """Return consistent food information for the frontend."""

    result = dict(item)

    result["food_id"] = result["item_id"]
    result["available_quantity"] = result["quantity"]
    result["expiry_time"] = result["expires_at"]

    try:
        price = calculate_price(
            result["mrp"],
            result["expires_at"],
            quantity=1
        )

        result["discounted_price"] = price["final_unit_price"]
        result["expiry_discount"] = price["expiry_discount"]

    except ValueError:
        result["discounted_price"] = None
        result["expiry_discount"] = None

    return result


def add_food_item(vendor_id, name, mrp, quantity, expires_at,
                  category="Other", image_url=None):
    """Allow a vendor to add a surplus food item."""

    try:
        details = _validate_food_details(
            name, mrp, quantity, expires_at,
            category, image_url
        )
    except ValueError as error:
        return False, str(error)

    conn = get_connection()

    try:
        if not _is_vendor(conn, vendor_id):
            return False, "Only registered vendors can add food."

        conn.execute(
            """
            INSERT INTO food_items
            (vendor_id, name, mrp, quantity, expires_at,
             category, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (vendor_id, *details)
        )

        conn.commit()
        return True, "Food item added successfully!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_available_food():
    """Get active food listings with stock and valid expiry."""

    conn = get_connection()

    try:
        items = conn.execute(
            """
            SELECT
                f.item_id,
                f.vendor_id,
                f.name,
                f.mrp,
                f.quantity,
                f.expires_at,
                f.category,
                f.image_url,
                u.name AS vendor_name
            FROM food_items f
            JOIN users u ON f.vendor_id = u.user_id
            WHERE f.is_active = 1
              AND f.quantity > 0
              AND f.expires_at > ?
            ORDER BY f.expires_at ASC
            """,
            (datetime.now().strftime("%Y-%m-%d %H:%M"),)
        ).fetchall()

        return [_format_food_item(item) for item in items]

    finally:
        conn.close()


def get_vendor_food(vendor_id):
    """Get all listings belonging to a registered vendor."""

    conn = get_connection()

    try:
        if not _is_vendor(conn, vendor_id):
            return []

        items = conn.execute(
            """
            SELECT
                item_id,
                vendor_id,
                name,
                mrp,
                quantity,
                expires_at,
                category,
                image_url,
                is_active
            FROM food_items
            WHERE vendor_id = ?
            ORDER BY item_id DESC
            """,
            (vendor_id,)
        ).fetchall()

        return [_format_food_item(item) for item in items]

    finally:
        conn.close()


def update_food_item(vendor_id, item_id, name, mrp, quantity,
                     expires_at, category="Other", image_url=None):
    """Allow a vendor to update only their own listing."""

    try:
        details = _validate_food_details(
            name, mrp, quantity, expires_at,
            category, image_url
        )
    except ValueError as error:
        return False, str(error)

    conn = get_connection()

    try:
        if not _is_vendor(conn, vendor_id):
            return False, "Only registered vendors can update food."

        cursor = conn.execute(
            """
            UPDATE food_items
            SET name = ?,
                mrp = ?,
                quantity = ?,
                expires_at = ?,
                category = ?,
                image_url = ?
            WHERE item_id = ? AND vendor_id = ?
            """,
            (*details, item_id, vendor_id)
        )

        conn.commit()

        if cursor.rowcount == 0:
            return False, "Food item not found or you do not own it."

        return True, "Food item updated successfully!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def delete_food_item(vendor_id, item_id):
    """Deactivate a vendor's listing instead of permanently deleting it."""

    conn = get_connection()

    try:
        if not _is_vendor(conn, vendor_id):
            return False, "Only registered vendors can delete food."

        cursor = conn.execute(
            """
            UPDATE food_items
            SET is_active = 0
            WHERE item_id = ? AND vendor_id = ?
            """,
            (item_id, vendor_id)
        )

        conn.commit()

        if cursor.rowcount == 0:
            return False, "Food item not found or you do not own it."

        return True, "Food item removed successfully!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
