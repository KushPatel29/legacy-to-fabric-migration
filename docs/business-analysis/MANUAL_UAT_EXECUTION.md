# Run manual acceptance against the candidate actually reviewed

`python -m governance.uat_release` extracts the six manual criteria from the
existing backlog and binds a reviewer packet to the current PBIP candidate hash.
The [generated packet](../../output/uat_release.json) contains Given/When/Then
steps, expected outcomes and empty review records. The six stories remain pending;
existing Jira/Confluence states are not changed by automated validation.

For a genuine review, give the candidate and scenario to an independent person.
Record the result, role, reviewer label, evidence location, review time and exact
candidate hash. Log defects with severity, evidence and resolution/retest. Do not
publish a reviewer's name or quotation without their permission. A technical lead
must separately validate identity, authority and the business evidence.

The gate rejects stale-candidate reviews, unknown/duplicate scenarios, missing
evidence and open critical/high defects. An author/CI-labelled record cannot
establish independent human acceptance. Submitted labels are not authentication;
even a structurally complete submission grants no production authority.

The executable rehearsal stages the current artifact manifest, rejects tampering
without changing the last accepted slot, stages a labelled replay and restores
the previous candidate. These are local files, not Power BI Service workspaces.
The existing live-control-plane gap remains explicit. RLS testing in a service
must use the correct Viewer permissions and actual intended identities; an Admin
account's unrestricted view cannot demonstrate RLS enforcement.

For the workshop, use the existing conflict: Finance needs month-end continuity,
IT wants a faster retirement and users need preparation. Capture alternatives,
tradeoffs and a decision before changing a wave. The document supplies the task;
it does not claim a workshop has happened.
