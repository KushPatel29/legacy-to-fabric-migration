from copy import deepcopy

import pytest

from governance import uat_release as release


def test_current_manual_backlog_remains_pending():
    result = release.build()
    assert len(result["manual_scenarios"]) == 6
    assert result["readiness"]["status"] == "PENDING HUMAN UAT"
    assert result["review_records"] == []
    assert result["readiness"]["production_authorized"] is False
    assert all(result["offline_rehearsal"].values())


def test_stale_or_automated_acceptance_cannot_be_used():
    packet = release.candidate()
    record = {"scenario_id": release.scenarios()[0]["scenario_id"], "candidate_sha256": "old",
              "result": "PASS", "reviewer": "CI", "reviewer_role": "tester",
              "evidence_ref": "test-fixture", "reviewed_at": "2026-10-25T00:00:00Z"}
    result = release.readiness(packet, [record], [])
    assert result["status"] == "BLOCKED"
    assert any("another candidate" in item for item in result["blocks"])
    assert any("human review" in item for item in result["blocks"])


def test_high_defect_blocks_the_release():
    for defect in ({"status": "OPEN", "severity": "high"},
                   {"status": "open", "severity": "HIGH"},
                   {"status": "UNKNOWN", "severity": "low"},
                   {"status": "OPEN", "severity": "unknown"}, None):
        result = release.readiness(release.candidate(), [], [defect])
        assert result["status"] == "BLOCKED"


def test_modified_manifest_is_not_a_verified_candidate():
    packet = deepcopy(release.candidate())
    packet["files"]["../outside.json"] = "fake"
    assert not release.verify_candidate(packet)
    for name in ("C:\\outside.json", "C:/outside.json", "/outside.json", "../outside.json"):
        body = {key: value for key, value in release.candidate().items() if key != "candidate_sha256"}
        body["files"][name] = "a" * 64
        assert not release.verify_candidate({**body, "candidate_sha256": release.digest(body)})


def test_empty_release_and_missing_rollback_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        release.candidate(tmp_path)
    with pytest.raises(ValueError):
        release.OfflineSlots(tmp_path).rollback()
