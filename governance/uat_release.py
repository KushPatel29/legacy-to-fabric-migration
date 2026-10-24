"""Bind manual UAT to an exact PBIP candidate and fail closed on missing review.

Offline release slots exercise integrity/rollback only. They are not Fabric or
Power BI Service workspaces, and submitted reviewer labels are not authenticated.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "docs/business-analysis/BACKLOG_AND_ACCEPTANCE.md"
PBIP = ROOT / "powerbi/pbip"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def candidate(source=PBIP):
    files = {}
    source = source.resolve()
    for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
        if not path.is_file() or ".pbi" in path.parts:
            continue
        if not path.resolve().is_relative_to(source):
            raise ValueError("Candidate must not follow links outside its source")
        payload = path.read_bytes()
        if path.suffix in {".json", ".tmdl", ".pbir", ".pbism", ".pbip", ".md"} or path.name == ".platform":
            payload = payload.replace(b"\r\n", b"\n")
        files[path.relative_to(source).as_posix()] = hashlib.sha256(payload).hexdigest()
    if not files:
        raise ValueError("An empty release is not a candidate")
    body = {"schema_version": 1, "files": files,
            "hash_basis": "PBIP text normalized to LF; other file bytes unchanged"}
    return {**body, "candidate_sha256": digest(body)}


def verify_candidate(packet):
    body = dict(packet)
    claimed = body.pop("candidate_sha256", None)
    files = body.get("files", {})
    if not isinstance(files, dict) or not files:
        return False
    if any(not isinstance(name, str) or not name or "\\" in name or ":" in name
           or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
           or not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
           for name, value in files.items()):
        return False
    return claimed == digest(body)


def scenarios():
    story = None
    result = []
    for line in BACKLOG.read_text(encoding="utf-8").splitlines():
        match = re.match(r"### (US-\d+) · (.*)", line)
        if match:
            story = match.group(1)
        if "| manual:" in line:
            cells = [value.strip() for value in line.strip("|").split("|")]
            result.append({"scenario_id": f"{story}:{cells[0]}", "story_id": story,
                           "given": cells[1], "when": cells[2], "expected": cells[3],
                           "source_status": cells[4], "result": "NOT_RUN"})
    if not result:
        raise ValueError("No manual criteria found; inspect the backlog parser")
    return result


def readiness(packet, records, defects):
    blocks, pending = [], []
    expected = {item["scenario_id"] for item in scenarios()}
    if not verify_candidate(packet):
        blocks.append("candidate integrity failed")
    supplied = {}
    for record in records:
        key = record.get("scenario_id")
        if key not in expected or key in supplied:
            blocks.append("unknown or duplicate manual scenario")
            continue
        supplied[key] = record
        if record.get("candidate_sha256") != packet.get("candidate_sha256"):
            blocks.append(f"{key}: review belongs to another candidate")
        if record.get("result") != "PASS":
            pending.append(key)
        if not all(str(record.get(field, "")).strip() for field in ("reviewer", "reviewer_role", "evidence_ref", "reviewed_at")):
            blocks.append(f"{key}: review evidence is incomplete")
        if str(record.get("reviewer", "")).strip().casefold() in {"kush patel", "author", "automated", "ci"}:
            blocks.append(f"{key}: independent human review is not established")
    pending.extend(sorted(expected - set(supplied)))
    for item in defects:
        if not isinstance(item, dict):
            blocks.append("invalid defect record")
            continue
        status = str(item.get("status", "")).strip().upper()
        severity = str(item.get("severity", "")).strip().lower()
        if status not in {"OPEN", "IN_PROGRESS", "CLOSED"} or severity not in {"critical", "high", "medium", "low"}:
            blocks.append("invalid defect status/severity")
        elif status != "CLOSED" and severity in {"critical", "high"}:
            blocks.append("open critical/high defect")
    return {"status": "BLOCKED" if blocks else "PENDING HUMAN UAT" if pending else "SUBMISSIONS READY FOR OWNER VERIFICATION",
            "blocks": sorted(set(blocks)), "pending_scenarios": sorted(set(pending)),
            "submitted_reviews": len(supplied), "production_authorized": False,
            "identity_boundary": "Submitted reviewer labels are unverified; the tool does not authenticate people or grant deployment authority."}


class OfflineSlots:
    """Single-process local rehearsal; never sends a cloud request."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.previous = None

    def stage(self, packet):
        if not verify_candidate(packet):
            raise ValueError("Candidate integrity failed")
        target = self.folder / "current.json"
        prior = json.loads(target.read_text()) if target.exists() else None
        staged = self.folder / "next.json"
        staged.write_text(json.dumps(packet, sort_keys=True), encoding="utf-8")
        staged.replace(target)
        self.previous = prior

    def rollback(self):
        if self.previous is None:
            raise ValueError("No previous verified release")
        prior = self.previous
        self.stage(prior)


def build():
    packet = candidate()
    checks = {}
    with tempfile.TemporaryDirectory(prefix="migration-release-") as folder:
        slots = OfflineSlots(folder)
        slots.stage(packet)
        baseline = json.loads((Path(folder) / "current.json").read_text())
        tampered = json.loads(json.dumps(packet))
        first = next(iter(tampered["files"]))
        tampered["files"][first] = "tampered"
        try:
            slots.stage(tampered)
        except ValueError:
            checks["tampered_candidate_rejected"] = True
        checks["failed_stage_preserves_previous"] = json.loads((Path(folder) / "current.json").read_text()) == baseline
        replay_body = {key: value for key, value in packet.items() if key != "candidate_sha256"}
        replay_body["rehearsal_label"] = "replay only; deployable source unchanged"
        replay = {**replay_body, "candidate_sha256": digest(replay_body)}
        slots.stage(replay)
        slots.rollback()
        checks["rollback_restores_previous_candidate"] = json.loads((Path(folder) / "current.json").read_text()) == baseline
    if len(checks) != 3 or not all(checks.values()):
        raise AssertionError(checks)
    return {"schema_version": 1, "candidate": packet, "manual_scenarios": scenarios(),
            "review_records": [], "defects": [], "readiness": readiness(packet, [], []),
            "offline_rehearsal": checks,
            "boundary": "Local artifact integrity/rollback exercise only. No Power BI Service publication, authenticated reviewer approval or completed manual UAT is claimed."}


if __name__ == "__main__":
    result = build()
    output = ROOT / "output/uat_release.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manual_scenarios": len(result["manual_scenarios"]), "readiness": result["readiness"], "rehearsal": result["offline_rehearsal"]}, indent=2))
