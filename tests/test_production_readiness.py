from pathlib import Path
from uuid import UUID

import pytest

from governance.build_production_evidence import (
    REQUIRED_EVIDENCE,
    build_packet,
    canonical_sha256,
    cyclonedx_sbom,
    direct_dependencies,
    evidence_hashes,
    verify_packet_digest,
)


ROOT = Path(__file__).resolve().parent.parent


def test_every_direct_dependency_is_exactly_pinned_and_conflict_free():
    dependencies = direct_dependencies()
    assert {item["name"] for item in dependencies} == {
        "faker",
        "numpy",
        "pandas",
        "plotly",
        "streamlit",
    }
    assert all(item["version"] for item in dependencies)


def test_unpinned_dependency_fails_closed(tmp_path, monkeypatch):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pandas\n", encoding="utf-8")
    monkeypatch.setattr(
        "governance.build_production_evidence.REQUIREMENT_FILES", (requirements,)
    )
    with pytest.raises(ValueError, match="unpinned direct dependency"):
        direct_dependencies()


def test_sbom_is_cyclonedx_and_labels_its_direct_dependency_boundary():
    sbom = cyclonedx_sbom(direct_dependencies())
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert UUID(sbom["serialNumber"].removeprefix("urn:uuid:"))
    assert len(sbom["components"]) == 5
    assert all(component["purl"].startswith("pkg:pypi/") for component in sbom["components"])
    assert "Direct Python dependencies only" in sbom["metadata"]["properties"][0]["value"]


def test_required_evidence_is_present_and_integrity_hashed():
    hashes = evidence_hashes()
    assert set(hashes) == set(REQUIRED_EVIDENCE)
    assert all(len(item["sha256"]) == 64 for item in hashes.values())


def test_release_packet_approves_only_the_public_synthetic_demo():
    packet, _ = build_packet()
    assert packet["public_demo_decision"] == "APPROVE PUBLIC DEMONSTRATION"
    assert packet["production_decision"] == "NOT AUTHORIZED"
    assert packet["status_counts"] == {"PASS": 8, "REVIEW": 3, "BLOCK": 0}


def test_packet_keeps_auth_telemetry_and_live_fabric_as_open_reviews():
    packet, _ = build_packet()
    reviews = {gate["control"] for gate in packet["gates"] if gate["status"] == "REVIEW"}
    assert reviews == {"PRD-09", "PRD-10", "PRD-11"}


def test_packet_digest_verifies_and_detects_tampering():
    packet, _ = build_packet()
    assert verify_packet_digest(packet)
    packet["production_decision"] = "AUTHORIZED"
    assert not verify_packet_digest(packet)


def test_canonical_digest_is_key_order_independent():
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})


def test_decision_engine_benchmark_retains_the_full_screened_programme():
    packet, _ = build_packet()
    assert packet["benchmark"]["passed"] is True
    assert packet["benchmark"]["scheduled_assets"] == 50
    assert packet["benchmark"]["p95_ms"] <= packet["benchmark"]["target_p95_ms"]
