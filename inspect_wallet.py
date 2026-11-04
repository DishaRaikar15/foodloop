import sqlite3

conn = sqlite3.connect("foodloop.db")
conn.row_factory = sqlite3.Row

print("DUPLICATE WALLET TRANSACTIONS:")

rows = conn.execute("""
    SELECT *
    FROM wallet_transactions
    WHERE user_id = ?
      AND kind = ?
      AND order_id = ?
""", (7, "earned", 7)).fetchall()

for row in rows:
    print(dict(row))

print("\nRELATED ORDER:")

order = conn.execute("""
    SELECT *
    FROM orders
    WHERE order_id = ?
""", (7,)).fetchone()

print(dict(order) if order else "Order not found")

conn.close()