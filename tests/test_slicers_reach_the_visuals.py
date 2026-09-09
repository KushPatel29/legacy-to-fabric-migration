"""A slicer must reach every visual on its page.

The failure this catches is silent, which is what makes it worth a test. A
running total needs to clear the date filter the axis puts on it, and the
shortest way to write that is `ALL(fact_table)`. That clears the date - and
every slicer on the page as well. The chart keeps rendering, the numbers stay
plausible, and the only symptom is that one line does not move when the user
filters. On the command centre page the Domain and Source Type slicers moved
four visuals out of five; the cutover burn-up stayed at the whole-estate total.

So: for each page, take the columns its slicers filter, walk every measure the
page's visuals use (and the measures those call), and fail if any of them
releases a column a slicer on that page is holding.

What is allowed, and why:

* `ALL(t[other_column])` - a running total releasing its own date column while
  the slicer holds a different one is the correct pattern, not a defect.
* `ALLSELECTED(...)` - explicitly respects the slicer; that is its purpose.
* `ALLEXCEPT(t, t[col])` - names the column it is keeping.
* A page with no slicers has nothing to contradict.

Nothing here is specific to one report; the pages and the model are both read
off disk, so this file drops into any PBIP repo unchanged.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PBIP = ROOT / "powerbi" / "pbip"
SM = next(PBIP.glob("*.SemanticModel")) / "definition"
PAGES = next(PBIP.glob("*.Report")) / "definition" / "pages"

# `measure 'Name' =` or `measure Name =`, then the DAX that follows. TMDL
# indents a measure body one level deeper than the `measure` line and closes it
# with two-tab properties (formatString, lineageTag, displayFolder), so the body
# ends at the first of those - or at the next declaration, or at the `///`
# comment introducing the next measure. Stopping only at the next declaration
# swallows all three, which is how this checker first reported a DIVIDE() of two
# measures as releasing a filter: it was reading the sentence that documents the
# fix, two measures further down.
MEASURE_RE = re.compile(
    r"^\tmeasure\s+(?:'([^']+)'|([A-Za-z_][\w ]*?))\s*=\s*"
    r"(.*?)(?=^\t\t[A-Za-z]\w*:|^\t(?:measure|column|partition|annotation)\s|^\t///|\Z)",
    re.M | re.S,
)
# ALL / REMOVEFILTERS / ALLEXCEPT and their first argument.
RELEASE_RE = re.compile(
    r"\b(ALL|REMOVEFILTERS|ALLEXCEPT)\s*\(\s*('[^']+'|[A-Za-z_]\w*)\s*(\[[^\]]+\])?",
    re.I,
)


def _unquote(name):
    return name[1:-1] if name.startswith("'") else name


def measures():
    """measure name -> DAX body, across every table in the model."""
    out = {}
    for f in sorted((SM / "tables").glob("*.tmdl")):
        for quoted, bare, body in MEASURE_RE.findall(f.read_text(encoding="utf-8")):
            out[(quoted or bare).strip()] = body
    return out


MEASURES = measures()


def _referenced_measures(body, seen):
    """Measures called from a DAX body, transitively."""
    for name in re.findall(r"\[([^\]]+)\]", body):
        if name in MEASURES and name not in seen:
            seen.add(name)
            _referenced_measures(MEASURES[name], seen)
    return seen


def pages():
    for page_dir in sorted(p for p in PAGES.iterdir() if p.is_dir()):
        visuals = sorted((page_dir / "visuals").glob("*/visual.json"))
        if visuals:
            yield page_dir.name, visuals


def page_facts(visuals):
    """(columns the page's slicers hold, measures the page's visuals use)."""
    held, used = set(), set()
    for v in visuals:
        raw = v.read_text(encoding="utf-8")
        refs = set(re.findall(r'"queryRef"\s*:\s*"([^"]+)"', raw))
        if json.loads(raw).get("visual", {}).get("visualType") == "slicer":
            held |= {r for r in refs if "." in r}
        used |= {r.split(".", 1)[1] for r in refs if r.split(".", 1)[1] in MEASURES}
    return held, used


CASES = [pytest.param(name, vs, id=name) for name, vs in pages()]


def test_the_measure_bodies_parsed_out_of_the_model_are_dax():
    """The regex above is load-bearing: if it over-captures, this file reports
    defects that are really the next measure's text, and if it under-captures it
    reports nothing at all. Both failure modes are quiet, so pin the shape."""
    assert len(MEASURES) > 5, "no measures parsed out of the model"
    stray = {n for n, b in MEASURES.items() if "lineageTag" in b or "formatString" in b}
    assert not stray, f"measure bodies ran past their DAX into properties: {sorted(stray)}"


def test_the_report_has_pages_with_slicers():
    """Guard against the traversal silently finding nothing."""
    assert any(page_facts(vs)[0] for _, vs in pages()), "no slicers found to check"


@pytest.mark.parametrize("page,visuals", CASES)
def test_no_measure_on_a_page_releases_a_column_its_slicer_holds(page, visuals):
    held, used = page_facts(visuals)
    if not held:
        pytest.skip(f"{page} has no slicers")

    reachable = set(used)
    for m in used:
        _referenced_measures(MEASURES[m], reachable)

    problems = []
    for name in sorted(reachable):
        body = MEASURES[name]
        for func, table, column in RELEASE_RE.findall(body):
            table = _unquote(table)
            if column:  # ALL(t[col]) releases exactly that column
                released = {f"{table}.{column[1:-1]}"}
            elif func.upper() == "ALLEXCEPT":
                kept = {
                    f"{table}.{c}"
                    for c in re.findall(rf"{re.escape(table)}\[([^\]]+)\]", body)
                }
                released = {h for h in held if h.startswith(f"{table}.")} - kept
            else:  # ALL(t) / REMOVEFILTERS(t) releases the whole table
                released = {h for h in held if h.startswith(f"{table}.")}
            for h in sorted(released & held):
                problems.append(
                    f"[{name}] {func.upper()}({table}) releases {h}, "
                    f"which a slicer on {page} is holding"
                )

    assert not problems, (
        f"{page}: {len(problems)} measure(s) ignore a slicer on their own page:\n  "
        + "\n  ".join(problems)
    )
