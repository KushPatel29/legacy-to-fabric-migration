"""
Every dated row the report joins to a month has to find that month.

The programme calendar was typed out - eighteen months from July 2025 - and the
parallel runs begin in May 2025. Three validation runs matched no month, so Power
BI put them in the relationship's blank member: every month-sliced validation
visual quietly dropped them, and every total stayed right. Nothing errors when a
calendar is short; it has to be checked against the data it serves.

The month table now derives its range from the same files, and this holds it to
that: it must read them, take its span from them, and carry no literal date.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MODEL = next(ROOT.glob("powerbi/pbip/*.SemanticModel")) / "definition"
MIGRATION = ROOT / "data" / "migration"


def calendar_tmdl() -> str:
    return (MODEL / "tables" / "dim_month.tmdl").read_text(encoding="utf-8")


def months_the_facts_carry() -> set[str]:
    plan = pd.read_csv(MIGRATION / "migration_plan.csv", usecols=["actual_cutover"])
    runs = pd.read_csv(MIGRATION / "parallel_run_results.csv", usecols=["run_date"])
    dated = pd.concat([pd.to_datetime(plan["actual_cutover"], errors="coerce"),
                       pd.to_datetime(runs["run_date"], errors="coerce")]).dropna()
    return set(dated.dt.strftime("%Y-%m"))


def test_the_calendar_reads_the_files_it_has_to_cover():
    tmdl = calendar_tmdl()
    assert "migration_plan.csv" in tmdl and "parallel_run_results.csv" in tmdl
    assert "List.Min" in tmdl and "List.Max" in tmdl


def test_the_calendar_is_not_pinned_to_a_literal_date():
    assert not re.search(r"#date\(\d{4}", calendar_tmdl()), (
        "dim_month is typed out again - the next seed that moves will put rows in a "
        "blank month")


def test_every_joined_month_lies_inside_the_span_the_calendar_derives():
    """The derivation, replayed: min to max of the same columns, whole months."""
    months = months_the_facts_carry()
    first, last = min(months), max(months)
    span = pd.period_range(first, last, freq="M").strftime("%Y-%m")
    assert months <= set(span)
    assert first <= "2025-05", "the early parallel runs are what this test is for"


def test_both_month_joins_still_point_at_this_calendar():
    relationships = (MODEL / "relationships.tmdl").read_text(encoding="utf-8")
    for source in ("migration_artifacts.cutover_month", "validation_runs.run_month"):
        assert re.search(rf"fromColumn:\s*{re.escape(source)}\s*\n\s*toColumn:\s*dim_month\.month",
                         relationships), source
