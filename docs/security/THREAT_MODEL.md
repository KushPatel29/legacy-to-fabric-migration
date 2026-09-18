# Threat model — public asset and migration decision demonstration

## Decision and boundary

This repository may be published as a **read-only public demonstration using
deterministic synthetic data**. It is not authorized to process municipal,
employer, client, personal, financial-account or infrastructure-security data.
The live board produces planning evidence and downloadable scenario files; it
does not approve spending, change a system of record, dispatch work or execute a
Fabric migration.

## Assets and trust boundaries

| Asset | Boundary | Protection in this repository |
|---|---|---|
| Synthetic asset register and GIS layer | committed public source → deterministic builders | schema, key, WGS 84, lifecycle and exception tests; blocked records are not published or funded |
| Capital and service decision evidence | browser inputs → bounded in-process calculations | constrained sliders/selectors, deterministic formulas, acceptance tests and explicit non-approval status |
| Downloaded decision pack | app process → reviewer workstation | scenario manifest, evidence boundary, source-derived tables and integrity-tested generation |
| Migration comparison | legacy-mirror + Fabric-mirror outputs → validator | row count, totals, row-level checksum and deliberate corruption tests |
| Repository and CI | contributor commit → GitHub Actions | pull-request build, pinned direct Python dependencies and generated direct-dependency SBOM |

There is no authenticated user boundary in the public app. That is acceptable
only because all served data is synthetic and the app has no write path to an
external system.

## Abuse and failure cases

| Threat or failure | Current control | Residual risk / production requirement |
|---|---|---|
| Real or sensitive data committed accidentally | documented synthetic-only rule; deterministic fixture tests | add automated secret/PII scanning and a formal data-ingestion approval before any real source is allowed |
| Crafted scenario causes excessive work | finite enumerated controls and bounded numeric ranges | add request limits and load tests before multi-user production use |
| A blocked GIS/asset record enters a recommendation | fail-closed reconciliation and planning-readiness filters | retain independent data-owner review and exception workflow in production |
| Download is mistaken for an approved capital plan | every packet states conditional/non-approval boundary | authenticated approver, immutable audit event and system-of-record integration required |
| Dependency compromise | exact direct pins and CycloneDX direct-dependency inventory | add transitive lock, vulnerability scanning, provenance/attestation and patch SLA |
| Host outage or cold start | static screenshots and repository evidence remain available | external monitoring and observed SLO evidence are not yet implemented |
| Unauthorized access to real asset detail | no real data is accepted; public content only | production requires SSO, least-privilege roles, row/field controls and access review |
| Fabric credentials leak | no credentials are required or stored by the demo | use short-lived workload identity and a disposable test workspace for credentialed validation |

## Security decision

**Approved for a public synthetic read-only demonstration. Not authorized for
production data or operational approval.** Open risks PRD-09 through PRD-11 are
recorded in `output/production_readiness_packet.json`; closing them requires
operating evidence, not a wording change.
