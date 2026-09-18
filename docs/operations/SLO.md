# Service targets and evidence boundary

These are **targets for a portfolio demonstration**, not claims of observed
production attainment. The repository has no external telemetry store and no
multi-user production load test.

| Indicator | Target | Current evidence | Status |
|---|---:|---|---|
| Public app availability | 99.0% monthly | hosting platform only; no independent observation window | REVIEW |
| Warm decision-engine p95 | ≤ 2,000 ms | 20-iteration local in-process benchmark in the release packet | MEASURED LOCALLY |
| Cold start to interactive | ≤ 90 seconds | best-effort hosted demo; static fallback is always available | REVIEW |
| Scenario calculation errors | < 1% of submitted valid scenarios | CI and component tests, not production request telemetry | REVIEW |
| Evidence recovery point | zero unreviewed source change | deterministic committed sources and SHA-256 evidence hashes | VERIFIED FOR DEMO |
| Evidence recovery time | ≤ 30 minutes to revert to last green commit | procedure in the demo operations runbook | PROCEDURE TESTABLE |

Production promotion requires at least 30 days of independent availability,
latency and error telemetry, defined ownership/on-call coverage, a tested alert
path and load evidence at the expected concurrency.
