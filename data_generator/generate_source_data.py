"""
Synthetic source data for the Legacy-to-Fabric Migration project.

Generates a small OLTP-style sales dataset (Customers, Products, Orders)
that both the legacy stored-procedure ETL and the refactored Fabric
notebook consume identically, so their outputs can be diffed row-for-row
in the parallel-run validation step.

Usage:
    python generate_source_data.py
"""

import numpy as np
import pandas as pd
from faker import Faker
from pathlib import Path

fake = Faker()
Faker.seed(21)
np.random.seed(21)

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REGIONS = ["BC Lower Mainland", "BC Interior", "Alberta", "Ontario", "Quebec"]
CATEGORIES = ["Fresh Meat", "Deli", "Seafood", "Frozen"]

N_CUSTOMERS = 50
N_PRODUCTS = 40
N_ORDERS = 15000


def gen_customers():
    return pd.DataFrame([
        {"customer_id": i, "customer_name": fake.company(), "region": np.random.choice(REGIONS)}
        for i in range(1, N_CUSTOMERS + 1)
    ])


def gen_products():
    return pd.DataFrame([
        {
            "product_id": i,
            "product_name": f"{np.random.choice(CATEGORIES)} {fake.word().capitalize()}",
            "category": np.random.choice(CATEGORIES),
            "unit_price": round(np.random.uniform(3, 45), 2),
        }
        for i in range(1, N_PRODUCTS + 1)
    ])


def gen_orders(customers, products):
    order_dates = pd.date_range("2025-01-01", "2025-06-30", freq="D")
    rows = []
    for i in range(1, N_ORDERS + 1):
        customer = customers.sample(1).iloc[0]
        product = products.sample(1).iloc[0]
        order_date = np.random.choice(order_dates)
        quantity = np.random.randint(1, 50)
        rows.append({
            "order_id": i,
            "order_date": pd.Timestamp(order_date).date(),
            "customer_id": customer["customer_id"],
            "product_id": product["product_id"],
            "quantity": quantity,
            "unit_price": product["unit_price"],
        })
    return pd.DataFrame(rows)


def main():
    customers = gen_customers()
    products = gen_products()
    orders = gen_orders(customers, products)

    customers.to_csv(OUT_DIR / "customers.csv", index=False)
    products.to_csv(OUT_DIR / "products.csv", index=False)
    orders.to_csv(OUT_DIR / "orders.csv", index=False)

    print(f"customers: {len(customers)} rows")
    print(f"products: {len(products)} rows")
    print(f"orders: {len(orders):,} rows")
    print(f"\nWrote CSVs to {OUT_DIR}")


if __name__ == "__main__":
    main()
