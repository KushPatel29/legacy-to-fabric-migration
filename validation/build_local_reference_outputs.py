"""
Local (pandas) stand-ins for the two real engines, so the parallel-run
validation script has something to diff today without requiring a live
SQL Server + Fabric trial. Each function independently re-implements the
same business logic as its real counterpart:

  build_legacy_output()  mirrors legacy/sql/02_usp_load_monthly_sales_summary.sql
  build_fabric_output()  mirrors fabric/notebooks/refactor_monthly_sales_summary.py

When you have SQL Server and Fabric actually running, replace these two
CSVs with real exports (SELECT * FROM dbo.RPT_MonthlySalesSummary, and the
Fabric notebook's own CSV export) — the validation script doesn't care
where the CSVs came from.

Usage:
    python build_local_reference_outputs.py
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent


def load_source():
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    return orders, customers, products


def build_legacy_output(orders, customers, products):
    """Mirrors the T-SQL: FORMAT(OrderDate,'yyyy-MM'), GROUP BY month/region/category.
    Revenue uses the order line's own unit_price (price at time of order),
    same as `o.UnitPrice` in the stored procedure — not the product master's
    current price, which could differ."""
    products_for_join = products[["product_id", "category"]]
    df = orders.merge(customers, on="customer_id").merge(products_for_join, on="product_id")
    df["report_month"] = pd.to_datetime(df["order_date"]).dt.strftime("%Y-%m")
    keys = ["report_month", "region", "category"]
    qty = df.groupby(keys)["quantity"].sum().rename("total_quantity")
    revenue = (
        (df["quantity"] * df["unit_price"])
        .groupby([df[k] for k in keys])
        .sum()
        .rename("total_revenue")
    )
    return pd.concat([qty, revenue], axis=1).reset_index()


def build_fabric_output(orders, customers, products):
    """Mirrors the PySpark: join then groupBy/agg — written independently
    of build_legacy_output() on purpose, so the validation step is a real
    check that both implementations agree, not a tautology."""
    products_for_join = products[["product_id", "category"]]
    joined = orders.merge(customers, on="customer_id").merge(products_for_join, on="product_id")
    joined["report_month"] = pd.to_datetime(joined["order_date"]).dt.strftime("%Y-%m")
    joined["line_revenue"] = joined["quantity"] * joined["unit_price"]

    grouped = joined.groupby(["report_month", "region", "category"]).agg(
        total_quantity=("quantity", "sum"),
        total_revenue=("line_revenue", "sum"),
    ).reset_index()
    return grouped


def main():
    orders, customers, products = load_source()

    legacy = build_legacy_output(orders, customers, products)
    fabric = build_fabric_output(orders, customers, products)

    legacy.to_csv(OUT_DIR / "legacy_output.csv", index=False)
    fabric.to_csv(OUT_DIR / "fabric_output.csv", index=False)

    print(f"legacy_output.csv: {len(legacy)} rows")
    print(f"fabric_output.csv: {len(fabric)} rows")


if __name__ == "__main__":
    main()
