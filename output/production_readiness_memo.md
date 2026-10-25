# Production-readiness decision memo

**Public-demo decision:** APPROVE PUBLIC DEMONSTRATION  
**Production decision:** NOT AUTHORIZED  
**Control posture:** 8 PASS / 3 REVIEW / 0 BLOCK  
**Packet digest:** `aba578db81c941f21768a942ab0e059c92b0144e508be3f234a99d2d919ca9d0`

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

- No claim of City of Fernie, municipal, employer or client deployment.
- No authentication or production authorization workflow is implemented.
- External uptime and concurrent-user performance are targets, not observed SLO attainment.
- The SBOM covers direct pinned Python dependencies, not the resolved transitive environment.
- Fabric control-plane deployment is not executed; offline migration validation is.
