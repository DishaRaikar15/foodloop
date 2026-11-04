import math
from datetime import datetime


def get_expiry_discount(expires_at):
    """Calculate discount based on remaining time before expiry."""

    try:
        expiry_time = datetime.strptime(
            expires_at, "%Y-%m-%d %H:%M"
        )

        remaining_minutes = (
            expiry_time - datetime.now()
        ).total_seconds() / 60

    except (ValueError, TypeError):
        raise ValueError("Invalid expiry date or time.")

    if remaining_minutes <= 0:
        raise ValueError("This food item has expired.")

    if remaining_minutes <= 30:
        return 50
    elif remaining_minutes <= 60:
        return 40
    elif remaining_minutes <= 120:
        return 25
    elif remaining_minutes <= 180:
        return 15
    else:
        return 10



def calculate_price(mrp, expires_at, quantity=1):
    """Calculate expiry and group discounts consistently."""

    try:
        mrp = float(mrp)
        quantity = int(quantity)
    except (ValueError, TypeError):
        raise ValueError("Invalid price or quantity.")

    if not math.isfinite(mrp) or mrp <= 0:
        raise ValueError("Price must be greater than zero.")

    if quantity <= 0:
        raise ValueError("Quantity must be at least 1.")

    expiry_discount = get_expiry_discount(expires_at)

    # Apply expiry discount first.
    price_after_expiry = mrp * (
        1 - expiry_discount / 100
    )

    # Apply an additional group discount for 5+ portions.
    group_discount = 15 if quantity >= 5 else 0

    final_unit_price = price_after_expiry * (
        1 - group_discount / 100
    )

    # Round the unit price before calculating the total.
    final_unit_price = round(final_unit_price, 2)
    total_price = round(final_unit_price * quantity, 2)

    return {
        "mrp": round(mrp, 2),
        "expiry_discount": expiry_discount,
        "group_discount": group_discount,
        "final_unit_price": final_unit_price,
        "quantity": quantity,
        "total_price": total_price
    }

