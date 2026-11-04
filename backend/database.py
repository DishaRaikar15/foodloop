
import sqlite3
import threading
from pathlib import Path

# Database location: main FoodLoop project folder
DB_PATH = Path(__file__).resolve().parent.parent / "foodloop.db"
_CONNECTION_TIMEOUT_SECONDS = 15
_INITIALIZED = False
_INITIALIZE_LOCK = threading.Lock()


def _open_connection():
    """Open a raw SQLite connection without running initialization."""

    conn = sqlite3.connect(DB_PATH, timeout=_CONNECTION_TIMEOUT_SECONDS)
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_missing(conn, table_name, column_name, column_definition):
    """Safely add a column when it does not already exist."""

    existing_columns = {
        row["name"]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    if column_name not in existing_columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN "
            f"{column_name} {column_definition}"
        )


def initialize_database():
    """Create FoodLoop tables and safely migrate existing databases."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _open_connection()

    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript("""

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'vendor')),
            referral_code TEXT UNIQUE NOT NULL,
            referred_by INTEGER,
            first_purchase_done INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referred_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS food_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            mrp REAL NOT NULL CHECK(mrp > 0),
            quantity INTEGER NOT NULL CHECK(quantity >= 0),
            expires_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            category TEXT NOT NULL DEFAULT 'Other',
            image_url TEXT,
            FOREIGN KEY (vendor_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            qty INTEGER NOT NULL CHECK(qty > 0),
            unit_price REAL NOT NULL,
            points_used INTEGER DEFAULT 0,
            total_paid REAL NOT NULL,
            group_deal INTEGER DEFAULT 0,
            status TEXT DEFAULT 'placed'
                CHECK(status IN ('placed', 'collected', 'cancelled')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            collected_at TEXT,
            pickup_code_hash TEXT,
            pickup_code_encrypted TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_id) REFERENCES food_items(item_id)
        );

        CREATE TABLE IF NOT EXISTS wallet_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            points INTEGER NOT NULL,
            note TEXT,
            order_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );

        CREATE TABLE IF NOT EXISTS food_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weekday TEXT NOT NULL,
            item TEXT NOT NULL,
            prepared INTEGER NOT NULL,
            sold INTEGER NOT NULL,
            vendor_id INTEGER,
            FOREIGN KEY (vendor_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_user
        ON orders(user_id);

        CREATE INDEX IF NOT EXISTS idx_food_vendor
        ON food_items(vendor_id);

        CREATE INDEX IF NOT EXISTS idx_wallet_user
        ON wallet_transactions(user_id);

        CREATE INDEX IF NOT EXISTS idx_orders_status
        ON orders(status);

        """)

        # Safely migrate existing databases.
        _add_column_if_missing(
            conn, "orders", "pickup_code_hash", "TEXT"
        )

        _add_column_if_missing(
            conn, "orders", "pickup_code_encrypted", "TEXT"
        )

        _add_column_if_missing(
            conn, "food_items", "category",
            "TEXT NOT NULL DEFAULT 'Other'"
        )

        _add_column_if_missing(
            conn, "food_items", "image_url", "TEXT"
        )

        # Prevent duplicate wallet transactions for the same
        # user, transaction type, order and transaction note.
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_wallet_unique_order_kind
            ON wallet_transactions(
                user_id,
                kind,
                order_id,
                COALESCE(note, '')
            )
            WHERE order_id IS NOT NULL
        """)

        conn.commit()
        global _INITIALIZED
        _INITIALIZED = True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_connection():
    """
    Return an initialized database connection.

    Required tables and columns are created automatically
    if they do not exist.
    """

    global _INITIALIZED
    if not _INITIALIZED:
        with _INITIALIZE_LOCK:
            if not _INITIALIZED:
                initialize_database()
    return _open_connection()


if __name__ == "__main__":
    initialize_database()

    print("FoodLoop database initialized successfully!")
    print(f"Database location: {DB_PATH}")

    conn = _open_connection()

    try:
        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        print("\nTables found:")
        for table in tables:
            print("-", table["name"])

        print("\nFood item columns:")
        for column in conn.execute(
            "PRAGMA table_info(food_items)"
        ).fetchall():
            print("-", column["name"])

        print("\nOrder columns:")
        for column in conn.execute(
            "PRAGMA table_info(orders)"
        ).fetchall():
            print("-", column["name"])

    finally:
        conn.close()
