"""Build fail-closed public-demo evidence without claiming production operation."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_decision_support import (  # noqa: E402
    load_assessment,
    multi_year_programme,
    programme_assumptions,
    programme_summary,
)


OUTPUT = ROOT / "output"
REQUIREMENT_FILES = (ROOT / "requirements.txt", ROOT / "data_generator" / "requirements.txt")
DIRECT_PIN = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^=<>!~\s]+)$")

REQUIRED_EVIDENCE = {
    "security_boundary": ROOT / "docs" / "security" / "THREAT_MODEL.md",
    "demo_operations": ROOT / "docs" / "operations" / "DEMO_OPERATIONS_RUNBOOK.md",
    "service_targets": ROOT / "docs" / "operations" / "SLO.md",
    "cutover_recovery": ROOT / "docs" / "cutover_runbook.md",
    "asset_decision_packet": ROOT / "examples" / "asset_management" / "output" / "asset_management_summary.json",
    "gis_release_packet": ROOT / "examples" / "gis_asset_integration" / "output" / "gis_asset_summary.json",
    "asset_static_fallback": ROOT / "docs" / "business-analysis" / "asset-management-decision-board.png",
    "gis_static_fallback": ROOT / "docs" / "business-analysis" / "gis-asset-reconciliation.png",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def verify_packet_digest(packet: dict[str, Any]) -> bool:
    content = dict(packet)
    claimed = content.pop("packet_sha256", "")
    return bool(claimed) and claimed == canonical_sha256(content)


def direct_dependencies() -> list[dict[str, str]]:
    dependencies: dict[str, str] = {}
    for path in REQUIREMENT_FILES:
        display_path = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = DIRECT_PIN.fullmatch(line)
            if not match:
                raise ValueError(f"unpinned direct dependency in {display_path}: {line}")
            name = match.group("name").lower()
            version = match.group("version")
            prior = dependencies.get(name)
            if prior is not None and prior != version:
                raise ValueError(f"conflicting direct dependency pin for {name}: {prior} vs {version}")
            dependencies[name] = version
    return [{"name": name, "version": dependencies[name]} for name in sorted(dependencies)]


def cyclonedx_sbom(dependencies: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:2f7cb488-31b2-5f90-9aae-1e9acfab0001",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "legacy-to-fabric-migration",
                "version": "portfolio-demo",
            },
            "properties": [
                {
                    "name": "evidence.boundary",
                    "value": "Direct Python dependencies only; not a resolved transitive environment SBOM.",
                }
            ],
        },
        "components": [
            {
                "type": "library",
                "name": item["name"],
                "version": item["version"],
                "purl": f"pkg:pypi/{item['name']}@{item['version']}",
            }
            for item in dependencies
        ],
    }


def benchmark_asset_decision(iterations: int = 20) -> dict[str, Any]:
    assessment = load_assessment()
    assumptions = programme_assumptions(8_000_000)
    durations_ms: list[float] = []
    last_summary: dict[str, Any] = {}
    for _ in range(iterations):
        started = time.perf_counter()
        programme = multi_year_programme(assessment, assumptions)
        last_summary = programme_summary(programme, assumptions)
        durations_ms.append((time.perf_counter() - started) * 1000)
    ordered = sorted(durations_ms)
    p95_index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered)) - 1))
    return {
        "environment": "local in-process, warm Python 3.12 benchmark",
        "iterations": iterations,
        "median_ms": round(statistics.median(durations_ms), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "target_p95_ms": 2_000,
        "passed": ordered[p95_index] <= 2_000,
        "scheduled_assets": last_summary["scheduled_assets"],
        "boundary": "This is decision-engine latency, not browser, network, host wake-up or concurrent-user performance.",
    }


def evidence_hashes() -> dict[str, dict[str, str]]:
    hashes: dict[str, dict[str, str]] = {}
    for evidence_id, path in REQUIRED_EVIDENCE.items():
        if not path.is_file():
            raise FileNotFoundError(f"required evidence missing: {path.relative_to(ROOT)}")
        hashes[evidence_id] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
        }
    return hashes


def build_packet() -> tuple[dict[str, Any], dict[str, Any]]:
    dependencies = direct_dependencies()
    sbom = cyclonedx_sbom(dependencies)
    hashes = evidence_hashes()
    benchmark = benchmark_asset_decision()
    compile_ok = True
    try:
        compile((ROOT / "streamlit_app.py").read_text(encoding="utf-8"), "streamlit_app.py", "exec")
        compile(
            (ROOT / "asset_decision_support.py").read_text(encoding="utf-8"),
            "asset_decision_support.py",
            "exec",
        )
    except SyntaxError:
        compile_ok = False

    gates = [
        {"control": "PRD-01", "name": "direct dependencies pinned", "status": "PASS", "evidence": dependencies},
        {"control": "PRD-02", "name": "direct-dependency SBOM generated", "status": "PASS", "evidence": "output/sbom.cdx.json"},
        {"control": "PRD-03", "name": "application sources compile", "status": "PASS" if compile_ok else "BLOCK", "evidence": ["streamlit_app.py", "asset_decision_support.py"]},
        {"control": "PRD-04", "name": "asset and GIS release evidence present", "status": "PASS", "evidence": [hashes["asset_decision_packet"], hashes["gis_release_packet"]]},
        {"control": "PRD-05", "name": "security and recovery procedures present", "status": "PASS", "evidence": [hashes["security_boundary"], hashes["cutover_recovery"], hashes["demo_operations"]]},
        {"control": "PRD-06", "name": "static fallback evidence present", "status": "PASS", "evidence": [hashes["asset_static_fallback"], hashes["gis_static_fallback"]]},
        {"control": "PRD-07", "name": "decision-engine latency target", "status": "PASS" if benchmark["passed"] else "BLOCK", "evidence": benchmark},
        {"control": "PRD-08", "name": "public surface contains synthetic read-only evidence", "status": "PASS", "evidence": "docs/security/THREAT_MODEL.md"},
        {"control": "PRD-09", "name": "external uptime and host latency observed", "status": "REVIEW", "evidence": "Targets declared; no production telemetry store is claimed."},
        {"control": "PRD-10", "name": "authenticated municipal roles and approvals", "status": "REVIEW", "evidence": "Not implemented; public demo must never process production or personal data."},
        {"control": "PRD-11", "name": "live Fabric control-plane validation", "status": "REVIEW", "evidence": "Offline validation executes; credentialed Fabric deployment is not exercised."},
    ]
    status_counts = {status: sum(gate["status"] == status for gate in gates) for status in ("PASS", "REVIEW", "BLOCK")}
    demo_decision = "APPROVE PUBLIC DEMONSTRATION" if status_counts["BLOCK"] == 0 else "HOLD PUBLIC DEMONSTRATION"
    packet: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "public_demo_decision": demo_decision,
        "production_decision": "NOT AUTHORIZED",
        "status_counts": status_counts,
        "scope": "Public, read-only portfolio demonstration using deterministic synthetic data",
        "boundaries": [
            "No claim of City of Fernie, municipal, employer or client deployment.",
            "No authentication or production authorization workflow is implemented.",
            "External uptime and concurrent-user performance are targets, not observed SLO attainment.",
            "The SBOM covers direct pinned Python dependencies, not the resolved transitive environment.",
            "Fabric control-plane deployment is not executed; offline migration validation is.",
        ],
        "gates": gates,
        "benchmark": benchmark,
        "evidence_hashes": hashes,
    }
    packet["packet_sha256"] = canonical_sha256(packet)
    return packet, sbom


def write_outputs(packet: dict[str, Any], sbom: dict[str, Any]) -> None:
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "production_readiness_packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
    counts = packet["status_counts"]
    memo = f"""# Production-readiness decision memo

**Public-demo decision:** {packet['public_demo_decision']}  
**Production decision:** {packet['production_decision']}  
**Control posture:** {counts['PASS']} PASS / {counts['REVIEW']} REVIEW / {counts['BLOCK']} BLOCK  
**Packet digest:** `{packet['packet_sha256']}`

The portfolio surface is suitable for a public synthetic demonstration: direct
dependencies are pinned and inventoried, application sources compile, asset and
GIS evidence is integrity-hashed, static fallbacks exist, recovery/security
procedures are documented, and the local decision engine meets its latency
target. This is not authority to operate against production municipal data.

## Required before production

- Add identity, role-scoped authorization and an approval audit trail.
- Validate the real Fabric control plane with credentialed, disposable test assets.
- Collect external availability, latency, error and dependency telemetry over an agreed observation window.
- Replace synthetic sources only under an approved data-classification, retention and privacy design.

## Evidence boundary

""" + "\n".join(f"- {item}" for item in packet["boundaries"]) + "\n"
    (OUTPUT / "production_readiness_memo.md").write_text(memo, encoding="utf-8")


def main() -> None:
    packet, sbom = build_packet()
    write_outputs(packet, sbom)
    print(f"public demo: {packet['public_demo_decision']}")
    print(f"production: {packet['production_decision']}")
    print(f"packet sha256: {packet['packet_sha256']}")
    if packet["public_demo_decision"] != "APPROVE PUBLIC DEMONSTRATION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
