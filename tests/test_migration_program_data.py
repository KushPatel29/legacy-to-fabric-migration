"""
Invariants for the migration-program dataset (data/migration/*.csv).

These are the guarantees the Power BI Migration Command Center relies on:
if any of them break, the dashboard silently lies — so CI regenerates the
dataset and re-proves them on every push.
"""

import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MIG = ROOT / "data" / "migration"

VALID_STATUSES = {"Not Started", "In Progress", "Parallel Run",
                  "Cutover", "Retired", "Blocked"}


@pytest.fixture(scope="module")
def dataset():
    subprocess.run(
        [sys.executable, str(ROOT / "data_generator" / "generate_migration_program.py")],
        check=True)
    read = lambda n: list(csv.DictReader(open(MIG / n, encoding="utf-8")))
    return (read("migration_inventory.csv"),
            read("migration_plan.csv"),
            read("parallel_run_results.csv"))


def test_referential_integrity(dataset):
    inventory, plan, runs = dataset
    ids = {r["artifact_id"] for r in inventory}
    assert {r["artifact_id"] for r in plan} == ids, "plan must cover the estate 1:1"
    assert {r["artifact_id"] for r in runs} <= ids, "runs must reference known artifacts"


def test_statuses_valid(dataset):
    _, plan, _ = dataset
    assert {r["status"] for r in plan} <= VALID_STATUSES


def test_done_artifacts_have_actuals(dataset):
    _, plan, _ = dataset
    for r in plan:
        if r["status"] in ("Cutover", "Retired"):
            assert r["actual_cutover"], f"{r['artifact_id']} done but no actual_cutover"
            assert r["effort_actual_days"], f"{r['artifact_id']} done but no actual effort"


def test_done_artifacts_end_on_go(dataset):
    """An artifact cannot be Cutover/Retired unless its final parallel run was GO —
    the same gate the runnable validator in validation/ enforces."""
    _, plan, runs = dataset
    done = {r["artifact_id"] for r in plan if r["status"] in ("Cutover", "Retired")}
    final = {}
    for r in runs:
        k = r["artifact_id"]
        if k not in final or int(r["attempt"]) > int(final[k]["attempt"]):
            final[k] = r
    for aid in done:
        assert aid in final, f"done artifact {aid} has no validation run"
        assert final[aid]["verdict"] == "GO", f"done artifact {aid} final run is NO-GO"


def test_verdict_reason_consistency(dataset):
    _, _, runs = dataset
    for r in runs:
        checks_pass = (r["row_count_match"] == "True"
                       and r["control_totals_match"] == "True"
                       and r["checksum_match"] == "True")
        if r["verdict"] == "GO":
            assert checks_pass and not r["mismatch_reason"]
        else:
            assert r["mismatch_reason"], "NO-GO must carry a root cause"
