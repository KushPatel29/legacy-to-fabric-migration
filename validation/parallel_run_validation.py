"""
Parallel-run validation: compares the legacy stored-procedure output
against the Fabric notebook's output using the three checks a real cutover
runbook relies on — row counts, control totals, and a row-level checksum —
and reports go/no-go for retiring the legacy pipeline.

Usage:
    python parallel_run_validation.py
"""

import hashlib
import pandas as pd
from pathlib import Path

DIR = Path(__file__).resolve().parent
KEY_COLS = ["report_month", "region", "category"]
VALUE_COLS = ["total_quantity", "total_revenue"]


def row_checksum(df: pd.DataFrame) -> str:
    """Order-independent checksum: normalize dtypes, sort by key, concatenate, hash.

    Normalizing dtypes matters: pandas/Spark can round-trip the same value as
    int64 in one engine and float64 in the other (e.g. 2326 vs 2326.0) purely
    as a side effect of how each groupby/agg path is written, with no actual
    data difference. Hashing the raw string representation would flag that
    as a mismatch — exactly the kind of false positive a checksum-based
    cutover check needs to be immune to.
    """
    normalized = df.copy()
    normalized["total_quantity"] = normalized["total_quantity"].astype("int64")
    normalized["total_revenue"] = normalized["total_revenue"].round(2)
    sortable = normalized.sort_values(KEY_COLS).reset_index(drop=True)
    payload = sortable.to_csv(index=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def main():
    legacy = pd.read_csv(DIR / "legacy_output.csv")
    fabric = pd.read_csv(DIR / "fabric_output.csv")

    print("=" * 60)
    print("PARALLEL-RUN VALIDATION: legacy vs fabric")
    print("=" * 60)

    # 1. Row counts
    row_count_match = len(legacy) == len(fabric)
    print(f"\n[1] Row count check: legacy={len(legacy)}, fabric={len(fabric)} "
          f"-> {'PASS' if row_count_match else 'FAIL'}")

    # 2. Control totals
    control_ok = True
    for col in VALUE_COLS:
        legacy_total = legacy[col].sum()
        fabric_total = fabric[col].sum()
        diff = abs(legacy_total - fabric_total)
        passed = diff < 0.01
        control_ok &= passed
        print(f"[2] Control total ({col}): legacy={legacy_total:,.2f}, "
              f"fabric={fabric_total:,.2f}, diff={diff:,.4f} -> {'PASS' if passed else 'FAIL'}")

    # 3. Row-level checksum (catches mismatches control totals could mask,
    #    e.g. two rows with offsetting errors that still sum correctly)
    merged = legacy.merge(fabric, on=KEY_COLS, suffixes=("_legacy", "_fabric"), how="outer", indicator=True)
    only_in_legacy = merged[merged["_merge"] == "left_only"]
    only_in_fabric = merged[merged["_merge"] == "right_only"]
    print(f"\n[3] Keys only in legacy: {len(only_in_legacy)}")
    print(f"[3] Keys only in fabric: {len(only_in_fabric)}")

    both = merged[merged["_merge"] == "both"].copy()
    value_mismatches = both[
        (both["total_quantity_legacy"] != both["total_quantity_fabric"])
        | ((both["total_revenue_legacy"] - both["total_revenue_fabric"]).abs() > 0.01)
    ]
    print(f"[3] Rows with matching keys but different values: {len(value_mismatches)}")
    if len(value_mismatches) > 0:
        print(value_mismatches[KEY_COLS + ["total_quantity_legacy", "total_quantity_fabric",
                                            "total_revenue_legacy", "total_revenue_fabric"]].head(10))

    legacy_checksum = row_checksum(legacy)
    fabric_checksum = row_checksum(fabric)
    checksum_match = legacy_checksum == fabric_checksum
    print(f"\n[3] Legacy checksum:  {legacy_checksum[:16]}...")
    print(f"[3] Fabric checksum:  {fabric_checksum[:16]}...")
    print(f"[3] Checksum match -> {'PASS' if checksum_match else 'FAIL'}")

    # ---- Verdict ----
    all_pass = (
        row_count_match and control_ok and len(only_in_legacy) == 0
        and len(only_in_fabric) == 0 and len(value_mismatches) == 0 and checksum_match
    )
    print("\n" + "=" * 60)
    print(f"CUTOVER VERDICT: {'GO — safe to retire legacy pipeline' if all_pass else 'NO-GO — investigate discrepancies above'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
