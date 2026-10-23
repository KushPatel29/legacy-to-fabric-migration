"""
The backlog's acceptance criteria are only as good as the tests they name.

BACKLOG_AND_ACCEPTANCE.md says a story is accepted when its criteria pass, and
names the test that executes each one. A renamed or deleted test would leave the
page claiming coverage that no longer exists, and nobody reads a backlog closely
enough to notice. So: every cited test must exist, every Must requirement in the
register must have a story, every story must cite a requirement the register
defines (or say it is proposed), and the Jira import file must match the page.
"""
from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "docs" / "business-analysis"
BACKLOG = PACK / "BACKLOG_AND_ACCEPTANCE.md"
REGISTER = PACK / "PROCESS_AND_REQUIREMENTS.md"

spec = importlib.util.spec_from_file_location("backlog_csv", PACK / "backlog_csv.py")
backlog_csv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backlog_csv)

TEXT = BACKLOG.read_text(encoding="utf-8")
EPICS, STORIES = backlog_csv.parse(TEXT)
REQ = re.compile(r"\b(?:BR|FR|NFR|CHG)-\d+\b")


def register() -> dict[str, str]:
    """Requirement ID -> MoSCoW priority, from the register table."""
    rows = re.findall(r"^\| ((?:BR|FR|NFR|CHG)-\d+) \| .+? \| (\w+) \|", REGISTER.read_text(encoding="utf-8"), re.M)
    return dict(rows)


def test_the_page_parses_into_epics_and_stories():
    assert len(EPICS) >= 4 and len(STORIES) >= 12
    assert all(s["criteria"] for s in STORIES), "a story with no acceptance criteria"
    assert len({s["id"] for s in STORIES}) == len(STORIES)


CITED = sorted({ref for s in STORIES for c in s["criteria"]
                for ref in re.findall(r"`(tests/[\w/]+\.py::\w+)`", c["status"])})


def test_most_acceptance_criteria_run_in_ci():
    criteria = [c for s in STORIES for c in s["criteria"]]
    running = [c for c in criteria if c["status"].startswith("runs:")]
    assert len(CITED) >= 25
    assert len(running) / len(criteria) > 0.75


@pytest.mark.parametrize("ref", CITED)
def test_every_cited_test_exists(ref):
    path, name = ref.split("::")
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert name in names, f"{ref} is cited as acceptance but does not exist"


def test_every_criterion_says_whether_it_runs_or_is_manual():
    for s in STORIES:
        for c in s["criteria"]:
            assert c["status"].startswith(("runs: `tests/", "manual: ")), (s["id"], c["n"])


def test_every_must_requirement_has_a_story():
    musts = {rid for rid, prio in register().items() if prio == "Must"}
    covered = {r for s in STORIES for r in REQ.findall(s["requirement"])}
    assert musts - covered == set(), f"Must requirements with no story: {sorted(musts - covered)}"


def test_every_story_cites_a_real_requirement_or_says_it_is_proposed():
    known = set(register())
    for s in STORIES:
        cited = set(REQ.findall(s["requirement"]))
        proposed = "proposed" in s["requirement"]
        assert cited or proposed, s["id"]
        assert proposed or cited <= known, f"{s['id']} cites {sorted(cited - known)}, not in the register"


RANK = {"Must": 3, "Should": 2, "Could": 1, "Won't": 0}


def test_no_story_outranks_its_requirement():
    """A Should refinement of a Must requirement is normal; a Must story under a
    Should requirement would be priority inflation."""
    reg = register()
    for s in STORIES:
        for rid in REQ.findall(s["requirement"]):
            if rid in reg:
                assert RANK[s["priority"]] <= RANK[reg[rid]], f"{s['id']} is {s['priority']} but {rid} is {reg[rid]}"


def test_the_jira_import_file_matches_the_page():
    committed = (PACK / "backlog.csv").read_text(encoding="utf-8")
    assert committed == backlog_csv.render(TEXT), "run: python docs/business-analysis/backlog_csv.py"


def test_the_jira_payloads_carry_the_whole_backlog():
    """jira_rest.py turns the page into Jira REST payloads. Hold it to the page:
    every story under its epic, every criterion in its description, Done only
    where every criterion runs in CI, and labels Jira will accept."""
    import json as _json
    import sys as _sys

    _sys.path.insert(0, str(ROOT / "docs" / "business-analysis"))
    import jira_rest

    p = jira_rest.payloads("LFM")
    assert len(p["epics"]) == 5 and len(p["stories"]) == 16
    epics = {e["id"] for e in p["epics"]}
    for s in p["stories"]:
        assert s["epic"] in epics
        doc = _json.dumps(s["fields"]["description"])
        items = s["fields"]["description"]["content"][3]["content"]
        assert len(items) == s["criteria"]
        assert s["done"] == ("Manual:" not in doc)
        assert all(" " not in label for label in s["fields"]["labels"])
        assert "](" not in doc, "a markdown link leaked into Jira text"
    assert sum(s["done"] for s in p["stories"]) == 10
    page = (ROOT / "docs" / "business-analysis" / "BACKLOG_AND_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "5 epics and 16 stories" in page and "Ten stories" in page and "six with a manual" in page


def test_the_confluence_pages_are_the_repository_documents():
    """confluence_rest.py publishes the pack to Confluence. What was sent is
    committed; regenerate it from the Markdown and require the same bytes, and
    require every page to be well-formed storage XHTML with every epic and story
    linked to its Jira issue."""
    import json as _json
    import sys as _sys
    import xml.dom.minidom

    _sys.path.insert(0, str(PACK))
    import confluence_rest

    committed = (PACK / "confluence_payloads.json").read_text(encoding="utf-8")
    assert committed == confluence_rest.render(), "run: python docs/business-analysis/confluence_rest.py --json"
    p = _json.loads(committed)
    for page in [p["home"], *p["pages"]]:
        xml.dom.minidom.parseString(
            '<r xmlns:ac="http://atlassian.com/content">' + page["storage"] + "</r>")
        assert "](" not in page["storage"], f"a markdown link leaked into {page['title']}"
    backlog = next(pg["storage"] for pg in p["pages"] if pg["source"].endswith("BACKLOG_AND_ACCEPTANCE.md"))
    keys = _json.loads((PACK / "jira_issue_keys.json").read_text(encoding="utf-8"))
    assert set(keys) == {e["id"] for e in EPICS} | {s["id"] for s in STORIES}
    for item, key in keys.items():
        assert f"/browse/{key}\">{key}</a>" in backlog, item
    assert backlog.count("<td>Done</td>") == 10 and backlog.count("<td>To Do</td>") == 6
    assert len(p["remote_links"]) == len(keys)
