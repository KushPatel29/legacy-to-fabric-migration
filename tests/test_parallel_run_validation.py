"""
Tests for the parallel-run validation framework.

Two halves:
  1. The happy path — the two independent implementations (T-SQL-mirroring
     and PySpark-mirroring) of the monthly sales summary must agree,
     yielding a GO verdict.
  2. Negative tests — deliberately corrupt the fabric output in each of the
     ways a real migration goes wrong (dropped row, shifted value, extra
     key) and assert the validator flags NO-GO. A validation framework you
     never see fail is indistinguishable from one that doesn't work.

Run locally:
    python data_generator/generate_source_data.py
    python validation/build_local_reference_outputs.py
    pytest tests/ -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "validation"))

from parallel_run_validation import validate  # noqa: E402


@pytest.fixture(scope="session")
def outputs():
    legacy_path = ROOT / "validation" / "legacy_output.csv"
    if not legacy_path.exists():
        pytest.skip("Reference outputs not built — run validation/build_local_reference_outputs.py")
    return (
        pd.read_csv(legacy_path),
        pd.read_csv(ROOT / "validation" / "fabric_output.csv"),
    )


# ---------- Happy path ----------

def test_clean_parallel_run_is_go(outputs):
    legacy, fabric = outputs
    result = validate(legacy, fabric)
    assert result["verdict"] == "GO", f"clean run failed validation: {result}"


def test_checksum_ignores_dtype_formatting(outputs):
    """Regression test for the real bug hit during development: int64 vs
    float64 representations of identical values must not fail the checksum."""
    legacy, fabric = outputs
    fabric_as_float = fabric.copy()
    fabric_as_float["total_quantity"] = fabric_as_float["total_quantity"].astype("float64")
    assert validate(legacy, fabric_as_float)["verdict"] == "GO"


# ---------- Negative tests: every corruption class must be caught ----------

def test_dropped_row_is_nogo(outputs):
    legacy, fabric = outputs
    result = validate(legacy, fabric.iloc[1:])
    assert result["verdict"] == "NO-GO"
    assert not result["row_count_match"]
    assert result["only_in_legacy"] == 1


def test_shifted_value_is_nogo(outputs):
    legacy, fabric = outputs
    corrupted = fabric.copy()
    corrupted.loc[0, "total_revenue"] += 100.0
    result = validate(legacy, corrupted)
    assert result["verdict"] == "NO-GO"
    assert result["value_mismatches"] == 1


def test_offsetting_errors_still_caught(outputs):
    """Two errors that cancel out in the control total — the exact failure
    mode the row-level checks exist to catch."""
    legacy, fabric = outputs
    corrupted = fabric.copy()
    corrupted.loc[0, "total_revenue"] += 500.0
    corrupted.loc[1, "total_revenue"] -= 500.0
    result = validate(legacy, corrupted)
    assert all(result["control_totals"].values()), "control totals should NOT catch offsetting errors"
    assert result["verdict"] == "NO-GO", "row-level checks must catch what control totals miss"
    assert result["value_mismatches"] == 2


def test_extra_key_is_nogo(outputs):
    legacy, fabric = outputs
    extra = pd.DataFrame([{
        "report_month": "2025-07", "region": "Nowhere", "category": "Ghost",
        "total_quantity": 1, "total_revenue": 1.0,
    }])
    result = validate(legacy, pd.concat([fabric, extra], ignore_index=True))
    assert result["verdict"] == "NO-GO"
    assert result["only_in_fabric"] == 1
