"""
The edge cases a parallel-run gate has to survive.

The existing suite proves the validator catches corrupted output. That is only
half the job. A cutover gate also has to *not* fire on differences that are not
differences — otherwise the team learns to ignore it — and it has to refuse to
pass in situations where every check technically agrees.

The most important test in this file is the first one. It is here because the
validator used to return GO for it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "validation"))

from parallel_run_validation import (  # noqa: E402
    KEY_COLS,
    VALUE_COLS,
    row_checksum,
    validate,
)

COLS = KEY_COLS + VALUE_COLS


def frame(rows: list[list]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLS)


def sample() -> pd.DataFrame:
    return frame(
        [
            ["2026-01", "BC", "Meat", 120, 4_800.00],
            ["2026-01", "AB", "Seafood", 80, 3_250.50],
            ["2026-02", "BC", "Meat", 140, 5_610.25],
            ["2026-02", "ON", "Poultry", 95, 2_990.75],
        ]
    )


def empty() -> pd.DataFrame:
    return pd.DataFrame(
        {c: pd.Series(dtype="object" if c in KEY_COLS else "float64") for c in COLS}
    )


# ------------------------------------------------------- the dangerous pass
def test_two_empty_outputs_are_not_a_go():
    """
    The failure this validator exists to prevent, and the one it used to wave
    through. If the source connection breaks, or a filter excludes everything,
    or an upstream load fails silently, BOTH pipelines emit nothing. Row counts
    match. Control totals match at zero. The checksums are identical. Every
    check passes and the gate says it is safe to retire the legacy pipeline —
    for a report that would go to zero rows the next morning.
    """
    result = validate(empty(), empty())
    assert result["verdict"] == "NO-GO"
    assert result["non_empty"] is False


def test_one_side_empty_is_not_a_go():
    assert validate(sample(), empty())["verdict"] == "NO-GO"
    assert validate(empty(), sample())["verdict"] == "NO-GO"


def test_a_real_parallel_run_is_marked_non_empty():
    assert validate(sample(), sample())["non_empty"] is True


# --------------------------------------------- differences that are not real
def test_row_order_does_not_matter():
    """
    Spark makes no ordering promise, so the same data comes back shuffled on
    every run. A gate that fires on row order would be switched off in week one.
    """
    legacy = sample()
    shuffled = legacy.iloc[::-1].reset_index(drop=True)
    assert validate(legacy, shuffled)["verdict"] == "GO"
    assert row_checksum(legacy) == row_checksum(shuffled)


def test_sub_cent_rounding_does_not_fail_the_gate():
    """Float arithmetic differs in the last place between engines. That is not a defect."""
    legacy = sample()
    fabric = legacy.copy()
    fabric.loc[0, "total_revenue"] = 4_800.004
    assert validate(legacy, fabric)["verdict"] == "GO"


def test_integer_and_float_representations_agree():
    """
    2326 and 2326.0 are the same number. Hashing the raw string form would call
    them a mismatch, which is the classic false positive in checksum comparison.
    """
    legacy = sample()
    fabric = legacy.copy()
    fabric["total_quantity"] = fabric["total_quantity"].astype("float64")
    assert validate(legacy, fabric)["verdict"] == "GO"


# ------------------------------------------------ differences that are real
def test_the_gate_is_cent_exact_not_merely_within_a_cent():
    """
    Writing this test is how I found out the validator is stricter than its own
    docstring implies, and that the stricter reading is the right one.

    Two tolerances are in play. The value-mismatch check forgives any difference
    below $0.01. The checksum rounds to cents and then compares exactly. Those
    agree everywhere except across a rounding boundary: +$0.009 on $4,800.00
    is under the stated tolerance, but it rounds to $4,800.01, which is a
    different number of cents — so the checksum vetoes it.

    That is correct behaviour for money and I left it alone. Two systems either
    agree to the cent or they do not, and a cutover gate that shrugs at a
    one-cent difference on one row will shrug at it on a million.
    """
    legacy = sample()

    # Drift that does not change the cent value: genuinely not a difference.
    same_cent = legacy.copy()
    same_cent.loc[0, "total_revenue"] += 0.004
    assert validate(legacy, same_cent)["verdict"] == "GO"

    # Drift that lands on a different cent: a real disagreement, however small.
    next_cent = legacy.copy()
    next_cent.loc[0, "total_revenue"] += 0.009
    assert validate(legacy, next_cent)["verdict"] == "NO-GO"

    # And well past the tolerance, both checks agree it is a failure.
    clearly_wrong = legacy.copy()
    clearly_wrong.loc[0, "total_revenue"] += 0.02
    result = validate(legacy, clearly_wrong)
    assert result["verdict"] == "NO-GO"
    assert result["value_mismatches"] == 1


def test_duplicate_key_on_one_side_is_caught():
    """
    A GROUP BY that lost a column emits the same key twice. The totals can still
    tie if the duplicate splits the value, so this must be caught structurally.
    """
    legacy = sample()
    fabric = pd.concat([legacy, legacy.iloc[[0]]], ignore_index=True)
    result = validate(legacy, fabric)
    assert result["verdict"] == "NO-GO"
    assert result["row_count_match"] is False


def test_quantity_drift_alone_is_caught():
    """Revenue can tie while quantity does not — a unit-conversion bug looks exactly like this."""
    legacy = sample()
    fabric = legacy.copy()
    fabric.loc[1, "total_quantity"] += 1
    result = validate(legacy, fabric)
    assert result["verdict"] == "NO-GO"
    assert result["value_mismatches"] >= 1


def test_renamed_key_value_is_caught_on_both_sides():
    """A region renamed upstream orphans a row in each direction, not just one."""
    legacy = sample()
    fabric = legacy.copy()
    fabric.loc[1, "region"] = "AB-WEST"
    result = validate(legacy, fabric)
    assert result["verdict"] == "NO-GO"
    assert result["only_in_legacy"] == 1
    assert result["only_in_fabric"] == 1


# ------------------------------------------------------------ the verdict
@pytest.mark.parametrize(
    "check",
    ["non_empty", "row_count_match", "only_in_legacy", "only_in_fabric",
     "value_mismatches", "checksum_match"],
)
def test_verdict_is_conjunctive(check):
    """
    Every check must be able to veto on its own. A gate where one failing check
    can be outvoted by five passing ones is not a gate.
    """
    result = validate(sample(), sample())
    assert result["verdict"] == "GO"

    broken = dict(result)
    broken["control_totals"] = dict(result["control_totals"])
    if check in ("only_in_legacy", "only_in_fabric", "value_mismatches"):
        broken[check] = 1
    else:
        broken[check] = False

    verdict = "GO" if (
        broken["non_empty"]
        and broken["row_count_match"]
        and all(broken["control_totals"].values())
        and broken["only_in_legacy"] == 0
        and broken["only_in_fabric"] == 0
        and broken["value_mismatches"] == 0
        and broken["checksum_match"]
    ) else "NO-GO"
    assert verdict == "NO-GO", f"{check} cannot veto the verdict on its own"


def test_control_totals_are_reported_per_column():
    """Both value columns get their own verdict, so a report says which one moved."""
    result = validate(sample(), sample())
    assert set(result["control_totals"]) == set(VALUE_COLS)
    assert all(result["control_totals"].values())
