#!/usr/bin/env python3
"""Generate the local warehouse fixtures (deterministic, seed 42).

The generated CSVs model a small warehouse. Six data-quality issues are
planted deliberately — they are the labeled ground truth in
``fixtures/expected_exceptions.json`` that the classifier is scored against:

  orders     : duplicate order_id values            -> duplicate_key
  customers  : email ~30% null (threshold 5%)        -> null_rate
  products   : price 60% "N/A" strings (FLOAT col)   -> type_drift
  events     : all rows stale vs reference time      -> freshness
  inventory  : 120 rows vs expected minimum 500      -> row_count_anomaly
  payments   : expected column "currency" missing    -> schema_drift

Every other table/column is clean, so a correct engine reports exactly
these six exceptions. Run: python scripts/generate_fixtures.py
"""

from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(_BASE, "fixtures")
rng = random.Random(42)


def write_csv(name: str, fieldnames: list[str], rows: list[dict]) -> None:
    path = os.path.join(FIXTURES, f"{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def fresh_ts() -> str:
    base = datetime(2026, 10, 15)
    delta = timedelta(days=rng.randint(0, 4), hours=rng.randint(0, 23))
    return (base + delta).strftime("%Y-%m-%dT%H:%M:%S")


def main() -> None:
    # ---- orders: 200 clean rows + 2 duplicated order_id rows ----------------
    orders = []
    for i in range(200):
        orders.append({
            "order_id": 1001 + i,
            "customer_id": rng.randint(1, 150),
            "order_ts": fresh_ts(),
            "amount": f"{rng.uniform(10, 900):.2f}",
            "status": rng.choice(["PLACED", "SHIPPED", "DELIVERED"]),
        })
    for dup_id in (1050, 1075):  # planted duplicate keys
        row = next(r for r in orders if r["order_id"] == dup_id)
        orders.append(dict(row))
    rng.shuffle(orders)
    write_csv("orders", ["order_id", "customer_id", "order_ts", "amount", "status"],
              orders)

    # ---- customers: email ~30% empty (planted null-rate issue) --------------
    customers = []
    first = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Eli", "Ivy", "Owen", "Nia", "Leo"]
    last = ["Sharma", "Patel", "Nguyen", "Garcia", "Khan", "Brown", "Lee", "Diaz"]
    for i in range(150):
        email = "" if i % 10 < 3 else f"user{i + 1}@example.com"  # 45/150 = 30%
        customers.append({
            "customer_id": i + 1,
            "full_name": f"{rng.choice(first)} {rng.choice(last)}",
            "email": email,
            "signup_date": (f"20{rng.randint(22, 25)}-{rng.randint(1, 12):02d}"
                            f"-{rng.randint(1, 28):02d}"),
            "country": rng.choice(["US", "CA", "IN", "GB", "DE"]),
        })
    write_csv("customers", ["customer_id", "full_name", "email", "signup_date", "country"],
              customers)

    # ---- products: price 60% "N/A" in a FLOAT column (planted type drift) ---
    products = []
    for i in range(120):
        price = "N/A" if i % 5 < 3 else f"{rng.uniform(5, 500):.2f}"  # 72/120 = 60%
        products.append({
            "product_id": i + 1,
            "sku": f"SKU-{10000 + i}",
            "price": price,
            "category": rng.choice(["MEMORY", "STORAGE", "LOGIC", "SENSORS"]),
        })
    write_csv("products", ["product_id", "sku", "price", "category"], products)

    # ---- events: every timestamp stale (planted freshness issue) ------------
    events = []
    base = datetime(2026, 8, 28)
    for i in range(300):
        ts = base + timedelta(days=rng.randint(0, 4), hours=rng.randint(0, 23))
        events.append({
            "event_id": i + 1,
            "event_ts": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "event_type": rng.choice(["CLICK", "VIEW", "PURCHASE", "LOGIN"]),
            "user_id": rng.randint(1, 5000),
        })
    write_csv("events", ["event_id", "event_ts", "event_type", "user_id"], events)

    # ---- inventory: only 120 rows vs expected min 500 (planted volume issue)
    inventory = []
    for i in range(120):
        inventory.append({
            "product_id": i + 1,
            "warehouse": rng.choice(["BOISE", "AUSTIN", "PHOENIX"]),
            "quantity": rng.randint(0, 1000),
            "updated_at": fresh_ts(),
        })
    write_csv("inventory", ["product_id", "warehouse", "quantity", "updated_at"],
              inventory)

    # ---- payments: "currency" column missing entirely (planted schema drift)
    payments = []
    for i in range(180):
        payments.append({
            "payment_id": i + 1,
            "order_id": rng.randint(1001, 1200),
            "amount": f"{rng.uniform(10, 900):.2f}",
            "payment_ts": fresh_ts(),
            "method": rng.choice(["CARD", "ACH", "WIRE"]),
        })
    write_csv("payments", ["payment_id", "order_id", "amount", "payment_ts", "method"],
              payments)


if __name__ == "__main__":
    main()
