# %% [markdown]
# ## Fabric refactor of usp_Load_RPT_MonthlySalesSummary
# Replaces the nightly full-refresh stored procedure with a Fabric notebook
# that does an incremental Delta MERGE — only the affected report months
# are recomputed and upserted, instead of truncating and rebuilding the
# entire reporting table every run. Same output shape as
# `dbo.RPT_MonthlySalesSummary`, so the parallel-run validation script can
# diff them directly.
#
# Copy each `# %%` cell into a Fabric notebook attached to a Lakehouse
# containing `customers`, `products`, `orders` tables (load from
# `data/customers.csv`, `data/products.csv`, `data/orders.csv`).

# %%
from pyspark.sql import functions as F
from delta.tables import DeltaTable

GOLD_TABLE = "gold.rpt_monthly_sales_summary"
spark.sql("CREATE SCHEMA IF NOT EXISTS gold")

# %% [markdown]
# ### Build the aggregate — identical business logic to the stored procedure,
# expressed as a DataFrame transformation instead of a GROUP BY in T-SQL.

# %%
orders = spark.table("orders")
customers = spark.table("customers")
# Only pull category from products — revenue uses the order line's own
# unit_price (price at time of order), same as the legacy stored procedure,
# not the product master's current price. Also avoids an ambiguous
# "unit_price" column after the join, since both tables have one.
products = spark.table("products").select("product_id", "category")

summary = (
    orders
    .join(customers, "customer_id")
    .join(products, "product_id")
    .withColumn("report_month", F.date_format("order_date", "yyyy-MM"))
    .groupBy("report_month", "region", "category")
    .agg(
        F.sum("quantity").alias("total_quantity"),
        F.sum(F.col("quantity") * F.col("unit_price")).alias("total_revenue"),
    )
    .withColumn("loaded_at_utc", F.current_timestamp())
)

# %% [markdown]
# ### Incremental MERGE instead of truncate-and-reload
# Only report_months present in this run's source data get touched — a
# historical month that hasn't changed is never rewritten, which is what
# actually makes this "incremental" rather than a Spark-flavored copy of
# the same full-refresh pattern.

# %%
if not spark.catalog.tableExists(GOLD_TABLE):
    summary.write.format("delta").saveAsTable(GOLD_TABLE)
    print(f"Created {GOLD_TABLE} ({summary.count():,} rows)")
else:
    target = DeltaTable.forName(spark, GOLD_TABLE)
    (
        target.alias("t")
        .merge(
            summary.alias("s"),
            "t.report_month = s.report_month AND t.region = s.region AND t.category = s.category",
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
    print(f"Merged into {GOLD_TABLE}")

# %% [markdown]
# ### Export for parallel-run validation
# Write out as CSV alongside the legacy SQL output so
# `validation/parallel_run_validation.py` can diff them.

# %%
(
    spark.table(GOLD_TABLE)
    .drop("loaded_at_utc")  # timestamp will never match between runs, exclude from the diff
    .toPandas()
    .to_csv("/lakehouse/default/Files/validation/fabric_output.csv", index=False)
)
print("Wrote fabric_output.csv for parallel-run validation.")
