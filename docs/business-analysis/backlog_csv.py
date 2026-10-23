"""
Write backlog.csv, the Jira CSV import of BACKLOG_AND_ACCEPTANCE.md.

    python docs/business-analysis/backlog_csv.py

The Markdown page is the source. This turns each epic and story into a row with
the columns Jira's CSV importer maps by default (Issue Type, Summary, Epic Name,
Epic Link, Priority, Labels, Description, Acceptance Criteria), so the backlog can
be loaded into a project without retyping it. tests/test_backlog_traces_to_tests.py
regenerates it and fails if the committed file differs.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "BACKLOG_AND_ACCEPTANCE.md"
TARGET = HERE / "backlog.csv"

MOSCOW_TO_JIRA = {"Must": "Highest", "Should": "High", "Could": "Medium", "Won't": "Low"}
COLUMNS = ["Issue Type", "Issue ID", "Summary", "Epic Name", "Epic Link", "Priority", "Labels",
           "Description", "Acceptance Criteria"]


def parse(text: str) -> tuple[list[dict], list[dict]]:
    """Epics and stories, in page order."""
    epics, stories = [], []
    epic = None
    for block in re.split(r"\n(?=## Epic |### US-)", text):
        if block.startswith("## Epic "):
            m = re.match(r"## Epic (E\d+) — (.+)", block)
            epic = {"id": m.group(1), "title": m.group(2).strip()}
            epics.append(epic)
        elif block.startswith("### US-"):
            head = re.match(r"### (US-\d+) · (.+)", block)
            story = re.search(r"\*\*As\*\*\s+(.+?),\s+\*\*I want\*\*\s+(.+?),\s+\*\*so that\*\*\s+(.+?)\.\n", block, re.S)
            meta = re.search(r"Requirement: (.+?) · Priority: (\w+)", block)
            criteria = []
            for row in re.findall(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", block, re.M):
                n, given, when, then, status = row
                criteria.append({"n": int(n), "given": given, "when": when, "then": then, "status": status})
            stories.append({
                "id": head.group(1), "title": head.group(2).strip(), "epic": epic["id"],
                "as": " ".join(story.group(1).split()), "want": " ".join(story.group(2).split()),
                "so_that": " ".join(story.group(3).split()),
                "requirement": meta.group(1).strip(), "priority": meta.group(2), "criteria": criteria,
            })
    return epics, stories


def rows(epics: list[dict], stories: list[dict]) -> list[dict]:
    out = []
    for e in epics:
        out.append({"Issue Type": "Epic", "Issue ID": e["id"], "Summary": e["title"], "Epic Name": e["title"],
                    "Epic Link": "", "Priority": "", "Labels": "migration", "Description": "",
                    "Acceptance Criteria": ""})
    for s in stories:
        req = re.findall(r"\b(?:BR|FR|NFR|CHG)-\d+\b", s["requirement"])
        runs = all(c["status"].startswith("runs:") for c in s["criteria"])
        ac = "\n".join(f"{c['n']}. Given {c['given']}, when {c['when']}, then {c['then']}. "
                       f"[{c['status'].replace('`', '')}]" for c in s["criteria"])
        out.append({
            "Issue Type": "Story", "Issue ID": s["id"], "Summary": f"{s['id']} {s['title']}", "Epic Name": "",
            "Epic Link": s["epic"], "Priority": MOSCOW_TO_JIRA[s["priority"]],
            "Labels": " ".join(["migration", *[r.lower() for r in req], "automated-ac" if runs else "manual-ac"]),
            "Description": f"As {s['as']}, I want {s['want']}, so that {s['so_that']}. Requirement: {s['requirement']}.",
            "Acceptance Criteria": ac,
        })
    return out


def render(text: str) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows(*parse(text)))
    return buffer.getvalue()


def main() -> int:
    TARGET.write_text(render(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {TARGET.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
