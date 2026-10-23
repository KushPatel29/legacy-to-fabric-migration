"""
Publish the delivery pack to a Confluence Cloud space, linked to the Jira backlog.

    python docs/business-analysis/confluence_rest.py --json   # writes confluence_payloads.json

Each page is one Markdown document from this folder (or the cutover runbook),
converted to Confluence storage format: headings, paragraphs, lists, tables,
code and links, with relative links rewritten to this repository on GitHub. The
backlog page also links every epic and story to its Jira issue
(jira_issue_keys.json, read back from the Jira project after jira_rest.py loaded
it), and each Jira story gets a remote link back to that page.

The Markdown stays the source of truth. confluence_payloads.json is what was
sent; tests/test_backlog_traces_to_tests.py regenerates it and fails if the
committed file differs, so Confluence cannot quietly say something the
repository does not.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = "https://github.com/KushPatel29/legacy-to-fabric-migration"
JIRA = "https://kush29.atlassian.net"
KEYS = json.loads((HERE / "jira_issue_keys.json").read_text(encoding="utf-8"))
TARGET = HERE / "confluence_payloads.json"

SPACE = {
    "key": "LFM",
    "name": "Legacy-to-Fabric Migration",
    "description": "Delivery pack for the synthetic legacy-to-Microsoft-Fabric migration programme: "
                   "charter, stakeholders, requirements, backlog, RAID, status, change and cutover. "
                   "Published from github.com/KushPatel29/legacy-to-fabric-migration.",
}

# (title, source file) in the order they appear under the space home.
PAGES = [
    ("Project charter", HERE / "PROJECT_CHARTER.md"),
    ("Stakeholders and RACI", HERE / "STAKEHOLDER_AND_RACI.md"),
    ("Process and requirements", HERE / "PROCESS_AND_REQUIREMENTS.md"),
    ("Backlog and acceptance criteria", HERE / "BACKLOG_AND_ACCEPTANCE.md"),
    ("RAID register", HERE / "RAID_REGISTER.md"),
    ("Status report", HERE / "STATUS_REPORT.md"),
    ("Change and adoption plan", HERE / "CHANGE_AND_ADOPTION_PLAN.md"),
    ("Cutover runbook", ROOT / "docs" / "cutover_runbook.md"),
]
HOME_SOURCE = HERE / "README.md"


# ---------------------------------------------------------------- Markdown -> storage
def _href(target: str, source: Path) -> str:
    if re.match(r"[a-z]+://", target) or target.startswith("mailto:"):
        return target
    if target.startswith("#"):
        return target
    path, _, anchor = target.partition("#")
    resolved = (source.parent / path).resolve().relative_to(ROOT).as_posix()
    kind = "tree" if (ROOT / resolved).is_dir() else "blob"
    return f"{REPO}/{kind}/master/{resolved}" + (f"#{anchor}" if anchor else "")


def inline(text: str, source: Path) -> str:
    """Escape, then apply code spans, images, links, bold and italics."""
    spans: list[str] = []

    def keep(markup: str) -> str:
        spans.append(markup)
        return f"\x00{len(spans) - 1}\x00"

    # Links first: their text is converted on its own (it may hold code spans).
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                  lambda m: keep(f'<a href="{html.escape(_href(m.group(2), source))}">'
                                 f"{html.escape(m.group(1) or 'image', quote=False)} (image)</a>"), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  lambda m: keep(f'<a href="{html.escape(_href(m.group(2), source))}">'
                                 f"{inline(m.group(1), source)}</a>"), text)
    text = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{html.escape(m.group(1), quote=False)}</code>"), text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def to_storage(markdown: str, source: Path) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    i = 0
    if lines and lines[0].startswith("# "):  # the page title carries the H1
        i = 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(body).replace("]]>", "]]]]><![CDATA[>")
            out.append('<ac:structured-macro ac:name="code"><ac:plain-text-body>'
                       f"<![CDATA[{code}]]></ac:plain-text-body></ac:structured-macro>")
            continue
        heading = re.match(r"(#{1,6}) (.+)", line)
        if heading:
            level = min(len(heading.group(1)), 6)
            out.append(f"<h{level}>{inline(heading.group(2).strip(), source)}</h{level}>")
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            head = _cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(c, source)}</th>" for c in head)
            tr = "".join("<tr>" + "".join(f"<td>{inline(c, source)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f"<table><tbody><tr>{th}</tr>{tr}</tbody></table>")
            continue
        bullet = re.match(r"(\s*)([-*]|\d+\.) (.+)", line)
        if bullet:
            ordered = bullet.group(2)[0].isdigit()
            items: list[str] = []
            while i < len(lines):
                m = re.match(r"(\s*)([-*]|\d+\.) (.+)", lines[i])
                if m and m.group(2)[0].isdigit() == ordered:
                    items.append(m.group(3))
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t, source)}</li>" for t in items) + f"</{tag}>")
            continue
        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(q for q in quote if q), source)}</p></blockquote>")
            continue
        para = []
        while (i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "```", ">"))
               and not lines[i].lstrip().startswith("|") and not re.match(r"\s*([-*]|\d+\.) ", lines[i])):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para), source)}</p>")
    return "\n".join(out)


# ---------------------------------------------------------------- the pages
def _jira(key: str) -> str:
    return f'<a href="{JIRA}/browse/{key}">{key}</a>'


def backlog_storage() -> str:
    sys.path.insert(0, str(HERE))
    from backlog_csv import SOURCE, parse  # noqa: PLC0415

    text = SOURCE.read_text(encoding="utf-8")
    epics, stories = parse(text)
    automated = {s["id"]: all(c["status"].startswith("runs:") for c in s["criteria"]) for s in stories}
    rows = "".join(
        f"<tr><td>{_jira(KEYS[s['id']])}</td><td>{s['id']}</td><td>{html.escape(s['title'], quote=False)}</td>"
        f"<td>{_jira(KEYS[s['epic']])}</td><td>{html.escape(s['requirement'], quote=False)}</td>"
        f"<td>{s['priority']}</td>"
        f"<td>{sum(c['status'].startswith('runs:') for c in s['criteria'])} of {len(s['criteria'])}</td>"
        f"<td>{'Done' if automated[s['id']] else 'To Do'}</td></tr>"
        for s in stories)
    summary = (
        "<h2>Traceability: story, Jira issue, requirement, tests</h2>"
        "<p>Each story is a Jira issue in project LFM. A story is Done only when every one of its "
        "acceptance criteria runs in CI; a story with any manual criterion stays in To Do, because no "
        "UAT has been run.</p>"
        "<table><tbody><tr><th>Jira</th><th>Story</th><th>Title</th><th>Epic</th><th>Requirement</th>"
        f"<th>MoSCoW</th><th>Criteria in CI</th><th>Status</th></tr>{rows}</tbody></table>")
    body = to_storage(text, SOURCE)

    def link_heading(m: re.Match) -> str:
        level, inner = m.group(1), m.group(2)
        found = re.match(r"(US-\d+|Epic (E\d+))", inner)
        if not found:
            return m.group(0)
        key = KEYS[found.group(2) or found.group(1)]
        return f"<h{level}>{inner} · {_jira(key)}</h{level}>"

    body = re.sub(r"<h(\d)>((?:US-\d+|Epic E\d+)[^<]*)</h\1>", link_heading, body)
    return summary + "\n" + body


def home_storage() -> str:
    intro = ("<p>This space is published from the repository "
             f'<a href="{REPO}">legacy-to-fabric-migration</a> by '
             f'<a href="{REPO}/blob/master/docs/business-analysis/confluence_rest.py">confluence_rest.py</a>. '
             "The Markdown there is the source; the backlog is also a Jira project "
             f'(<a href="{JIRA}/jira/software/projects/LFM/boards">LFM</a>) with every story linked to its page '
             "here. The programme, organisations and registers are a portfolio simulation built on the "
             "repository's synthetic migration dataset, not a client engagement.</p>")
    return intro + "\n" + to_storage(HOME_SOURCE.read_text(encoding="utf-8"), HOME_SOURCE)


def payloads() -> dict:
    pages = []
    for title, source in PAGES:
        body = backlog_storage() if source.name == "BACKLOG_AND_ACCEPTANCE.md" else \
            to_storage(source.read_text(encoding="utf-8"), source)
        pages.append({"title": title, "source": source.relative_to(ROOT).as_posix(), "storage": body})
    return {
        "space": SPACE,
        "home": {"title": SPACE["name"], "source": HOME_SOURCE.relative_to(ROOT).as_posix(),
                 "storage": home_storage()},
        "pages": pages,
        "remote_links": [{"issue": KEYS[k], "story": k, "page": "Backlog and acceptance criteria"}
                         for k in sorted(KEYS) if k.startswith(("US-", "E"))],
    }


def render() -> str:
    return json.dumps(payloads(), indent=1, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="write confluence_payloads.json")
    args = ap.parse_args()
    if args.json:
        TARGET.write_text(render(), encoding="utf-8")
        print(f"wrote {TARGET.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
