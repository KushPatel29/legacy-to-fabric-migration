"""
Load the backlog into Jira Cloud through the REST API, as real issues.

    python docs/business-analysis/jira_rest.py --json > payloads.json   # what would be sent
    JIRA_BASE_URL=https://<site>.atlassian.net JIRA_EMAIL=... JIRA_API_TOKEN=... \\
        python docs/business-analysis/jira_rest.py --project LFM            # send it

backlog.csv suits Jira's CSV importer; this goes further. Each story becomes an
issue under its epic, with the user story as the description and the acceptance
criteria as a numbered list in Atlassian Document Format: each criterion links
the CI test that executes it, or says it is a manual UAT scenario. MoSCoW
priority becomes a label, because a team-managed project has no priority field
by default. A story is moved to Done only when every one of its criteria runs
in CI, which is this repository's Definition of Done; a story with any manual
criterion stays in To Do, because no UAT has been run.

The page (BACKLOG_AND_ACCEPTANCE.md) stays the source of truth: this reads it
through backlog_csv.parse, so the two cannot drift.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backlog_csv import SOURCE, parse  # noqa: E402

REPO = "https://github.com/KushPatel29/legacy-to-fabric-migration"
CI = f"{REPO}/actions/workflows/ci.yml"
PAGE = f"{REPO}/blob/master/docs/business-analysis/BACKLOG_AND_ACCEPTANCE.md"


def text(t: str, marks: list[dict] | None = None) -> dict:
    node = {"type": "text", "text": t}
    if marks:
        node["marks"] = marks
    return node


def link(t: str, href: str, code: bool = False) -> dict:
    marks = [{"type": "link", "attrs": {"href": href}}]
    if code:
        marks.insert(0, {"type": "code"})
    return text(t, marks)


def para(*content: dict) -> dict:
    return {"type": "paragraph", "content": list(content)}


def strip_links(s: str) -> str:
    """Markdown links read as their text: a relative link means nothing in Jira."""
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)


def runs_test(status: str) -> str | None:
    m = re.match(r"runs: `([^`]+)`", status)
    return m.group(1) if m else None


def criterion(c: dict) -> dict:
    sentence = strip_links(f"Given {c['given']}, when {c['when']}, then {c['then']}. ")
    test = runs_test(c["status"])
    if test:
        path = test.split("::")[0]
        tail = [text("Runs in CI: "), link(test, f"{REPO}/blob/master/{path}", code=True)]
    else:
        note = strip_links(c["status"].removeprefix("manual").strip(" :—-"))
        tail = [text(f"Manual: {note or 'UAT scenario'}.", [{"type": "em"}])]
    return {"type": "listItem", "content": [para(text(sentence), *tail)]}


def automated(story: dict) -> bool:
    return all(runs_test(c["status"]) for c in story["criteria"])


def story_description(s: dict) -> dict:
    return {"type": "doc", "version": 1, "content": [
        para(text("As "), text(s["as"], [{"type": "strong"}]), text(", I want "), text(s["want"]),
             text(", so that "), text(s["so_that"]), text(".")),
        para(text(f"Requirement {s['requirement']} · MoSCoW: {s['priority']}")),
        {"type": "heading", "attrs": {"level": 3}, "content": [text("Acceptance criteria")]},
        {"type": "orderedList", "content": [criterion(c) for c in s["criteria"]]},
        para(text("Source: "), link("BACKLOG_AND_ACCEPTANCE.md", PAGE),
             text(" · Definition of Done: every criterion that runs in CI passes on the default branch ("),
             link("CI", CI), text(").")),
    ]}


def epic_description(e: dict, stories: list[dict]) -> dict:
    mine = [s["id"] for s in stories if s["epic"] == e["id"]]
    return {"type": "doc", "version": 1, "content": [
        para(text(f"{e['id']}: {len(mine)} stories ({', '.join(mine)}). Synthetic migration programme: "),
             link("legacy-to-fabric-migration", REPO), text(".")),
    ]}


def labels(s: dict) -> list[str]:
    # Jira labels cannot contain spaces: keep the requirement IDs, and flag a
    # requirement the register does not yet hold.
    reqs = [r.lower() for r in re.findall(r"[A-Z]+-\d+", s["requirement"])]
    proposed = ["proposed-requirement"] if "proposed" in s["requirement"].lower() else []
    return ["migration", f"moscow-{s['priority'].lower()}", *reqs, *proposed,
            "automated-ac" if automated(s) else "manual-ac"]


def payloads(project: str) -> dict:
    epics, stories = parse(SOURCE.read_text(encoding="utf-8"))
    return {
        "epics": [{"id": e["id"], "fields": {
            "project": {"key": project}, "issuetype": {"name": "Epic"},
            "summary": f"{e['id']} {e['title']}", "labels": ["migration"],
            "description": epic_description(e, stories)}} for e in epics],
        "stories": [{"id": s["id"], "epic": s["epic"], "done": automated(s), "criteria": len(s["criteria"]),
                     "fields": {"project": {"key": project}, "issuetype": {"name": "Story"},
                                "summary": f"{s['id']} {s['title']}", "labels": labels(s),
                                "description": story_description(s)}} for s in stories],
    }


def send(base: str, auth: str, method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"{base}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Basic {auth}", "Accept": "application/json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def push(project: str) -> None:
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    auth = base64.b64encode(f"{os.environ['JIRA_EMAIL']}:{os.environ['JIRA_API_TOKEN']}".encode()).decode()
    p = payloads(project)
    keys = {}
    for e in p["epics"]:
        keys[e["id"]] = send(base, auth, "POST", "/rest/api/3/issue", {"fields": e["fields"]})["key"]
    for s in p["stories"]:
        fields = dict(s["fields"], parent={"key": keys[s["epic"]]})
        key = send(base, auth, "POST", "/rest/api/3/issue", {"fields": fields})["key"]
        if s["done"]:
            done = next(t for t in send(base, auth, "GET", f"/rest/api/3/issue/{key}/transitions")["transitions"]
                        if t["to"]["statusCategory"]["key"] == "done")
            send(base, auth, "POST", f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": done["id"]}})
        print(key, s["id"], "Done" if s["done"] else "To Do")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="LFM")
    ap.add_argument("--json", action="store_true", help="print the payloads instead of sending them")
    args = ap.parse_args()
    if args.json:
        json.dump(payloads(args.project), sys.stdout, indent=1)
        return 0
    push(args.project)
    return 0


if __name__ == "__main__":
    sys.exit(main())
