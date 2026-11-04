
from datetime import date, timedelta

from backend.database import get_connection


def get_user_rewards(user_id):
    """Calculate a student's achievements and collection streak."""

    conn = get_connection()

    try:
        # Get collected order statistics
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_orders,
                COALESCE(SUM(qty), 0) AS total_portions
            FROM orders
            WHERE user_id = ?
              AND status = 'collected'
            """,
            (user_id,)
        ).fetchone()

        # Get unique collection dates
        records = conn.execute(
            """
            SELECT DISTINCT DATE(collected_at) AS collection_date
            FROM orders
            WHERE user_id = ?
              AND status = 'collected'
              AND collected_at IS NOT NULL
            ORDER BY collection_date DESC
            """,
            (user_id,)
        ).fetchall()

        collection_dates = {
            date.fromisoformat(row["collection_date"])
            for row in records
        }

        total_orders = stats["total_orders"]
        total_portions = stats["total_portions"]

        # Calculate consecutive-day streak
        streak = 0
        current_day = date.today()

        if current_day not in collection_dates:
            current_day -= timedelta(days=1)

        while current_day in collection_dates:
            streak += 1
            current_day -= timedelta(days=1)

        # Determine achievements
        achievements = [
            {
                "name": "First Rescue",
                "description": "Complete your first food collection.",
                "unlocked": total_orders >= 1
            },
            {
                "name": "Food Saver",
                "description": "Collect 5 food portions.",
                "unlocked": total_portions >= 5
            },
            {
                "name": "Super Saver",
                "description": "Collect 10 food portions.",
                "unlocked": total_portions >= 10
            },
            {
                "name": "Regular Rescuer",
                "description": "Complete 5 collected orders.",
                "unlocked": total_orders >= 5
            },
            {
                "name": "3-Day Streak",
                "description": "Collect food on 3 consecutive days.",
                "unlocked": streak >= 3
            }
        ]

        unlocked_count = sum(
            1 for achievement in achievements
            if achievement["unlocked"]
        )

        return {
            "total_collected_orders": total_orders,
            "total_collected_portions": total_portions,
            "current_streak_days": streak,
            "achievements": achievements,
            "unlocked_achievements": unlocked_count,
            "total_achievements": len(achievements)
        }

    finally:
        conn.close()
