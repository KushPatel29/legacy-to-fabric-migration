# RAID Register

This sample register uses evidence and failure modes from the synthetic
migration programme. Owners are roles, and target dates are relative to a
wave rather than invented calendar commitments.

## Risks

| ID | Risk | Probability | Impact | Trigger | Mitigation and contingency | Owner | Status |
|---|---|---|---|---|---|---|---|
| R-01 | Legacy and Fabric outputs diverge on a business-critical report. | Medium | Critical | Any required validation check fails. | Block GO, identify the failing grain, remediate, and restart the clean-run window. | Technical lead | Open |
| R-02 | An undocumented consumer loses access after retirement. | Medium | High | Consumer discovered after requirements baseline. | Analyse query and subscription logs, confirm owners, retain legacy for one reporting cycle, and publish support contacts. | Business analyst | Open |
| R-03 | Role mappings expose restricted finance information. | Low | Critical | Security test returns an unexpected row or object. | Least-privilege review, role impersonation tests, and security approval before UAT. | Security lead | Open |
| R-04 | Business users cannot complete UAT within the wave schedule. | Medium | High | Less than 80% of planned cases executed halfway through the window. | Book testers during planning, nominate delegates, and move the cutover rather than waive critical coverage. | Business owner | Open |
| R-05 | Training or support material is outdated at cutover. | Medium | Medium | Material version does not match the release candidate. | Version training with the release, verify links at readiness review, and keep floor support during hypercare. | Change lead | Open |
| R-06 | Vendor or platform dependency delays configuration. | Medium | Medium | Dependency misses its committed date. | Track dependency separately, agree an escalation path, and preserve a legacy-wave fallback. | Programme manager | Open |

## Issues

| ID | Issue | Impact | Action | Owner | Status |
|---|---|---|---|---|---|
| I-01 | Equivalent integer and float values initially produced different raw checksums. | False NO-GO could undermine trust in the gate. | Normalise data types before hashing and retain regression coverage. | Technical lead | Resolved |
| I-02 | Two empty outputs initially returned GO because every comparison agreed at zero. | A failed source could approve an empty production report. | Add an explicit non-empty check and make it the first edge-case test. | Technical lead | Resolved |
| I-03 | Report repointing can succeed technically while subscriptions still target the old source. | Users may receive stale output after cutover. | Add subscription and connection verification to the readiness checklist. | Reporting lead | Open |

## Assumptions

| ID | Assumption | Validation method | Owner | Status |
|---|---|---|---|---|
| A-01 | Each Tier 1 artifact has an available business owner and tester. | Confirm during wave initiation. | Programme manager | To validate |
| A-02 | Legacy outputs can be retained for one full reporting cycle. | Confirm capacity and support approval before GO. | Technical lead | To validate |
| A-03 | Metric definitions are stable during a migration wave. | Check the decision log for approved metric changes. | Business analyst | To validate |

## Dependencies

| ID | Dependency | Needed by | Owner | Response if late |
|---|---|---|---|---|
| D-01 | Fabric environment and target access roles | Build start | Platform owner | Resequence to a discovery-only wave. |
| D-02 | Representative source extract | Functional testing | Source-system owner | Block validation; do not substitute unapproved data. |
| D-03 | Business-owner availability | Requirements and UAT | Business owner | Nominate an authorised delegate or move the wave. |
| D-04 | Service-desk knowledge article and escalation route | Readiness review | Service-desk lead | Extend hypercare and block retirement if support is unsafe. |

## Review Cadence

- Review weekly during planning and build.
- Review twice weekly during validation and daily during cutover or hypercare.
- Escalate a critical risk immediately rather than waiting for the next report.
- Close an item only when the evidence and closure decision are linked.
