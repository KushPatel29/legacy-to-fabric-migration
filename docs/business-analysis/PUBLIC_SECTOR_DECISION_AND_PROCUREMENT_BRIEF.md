# Public-Sector Decision and Procurement Brief

## Evidence Boundary

This is a jurisdiction-neutral portfolio scenario built around the synthetic
migration, Microsoft 365, and GIS evidence in this repository. It demonstrates
how I would structure a staff recommendation, an executive or Council-style
briefing, a fair vendor evaluation, and a policy-impact review. It does not
claim municipal employment, a completed procurement, legal advice, access to a
public body's systems, or approval by elected officials. Timelines are planning
assumptions to validate during discovery; no unverified savings are claimed.

## Decision Requested

Approve a controlled discovery and pilot for governed asset-information
integration. The pilot would connect an authoritative asset register, a GIS
layer, reporting, and programme records while preserving clear ownership,
security, audit history, accessibility, and a reversible release path.

Approval of the pilot would **not** approve a full platform replacement or a
vendor award. It would authorise staff to validate requirements, policy
constraints, costs, integration feasibility, user needs, and procurement
strategy before returning with a production recommendation.

## Why a Decision Is Needed

The synthetic current state has the same control problem seen in many
organisations: records are distributed across legacy reports, spreadsheets,
email, GIS files, and operational systems. Asset identity, geometry, lifecycle
status, financial context, approvals, and exception ownership can disagree.
That creates four material risks:

1. staff may act on a record whose location or status is stale;
2. a correction may be made in a downstream file instead of the authoritative
   source, so the error returns on the next refresh;
3. approvals and decisions may be difficult to retrieve or audit; and
4. a technically successful migration may still fail adoption, accessibility,
   security, records-management, or service-continuity expectations.

The repository already proves the control pattern on synthetic data: only four
of nine GIS features pass identity, geometry, and lifecycle checks, while five
deliberate exception classes are blocked and routed visibly. A discovery pilot
would test whether the same pattern is fit for a real operating context before
any production commitment.

## Options Considered

| Option | What it means | Advantages | Risks and limitations |
|---|---|---|---|
| 1. Maintain the current process | Keep existing files and reports; improve instructions and periodic manual reconciliation | Lowest immediate disruption; minimal procurement effort | Control remains dependent on people remembering manual steps; weak lineage and exception ownership; continuing support burden |
| 2. Governed integration pilot | Pilot stable asset keys, authoritative ownership, automated validation, an exception queue, role-based reporting, and controlled programme records | Tests value and feasibility at limited scope; produces evidence for cost and procurement decisions; reversible | Requires staff time, named owners, privacy/security review, and disciplined scope control |
| 3. Full platform replacement | Procure and implement a new enterprise asset, GIS, reporting, or workplace platform | Could address broader capability and technical-debt needs | Highest cost, change load, and lock-in risk; requirements and data quality may still be unresolved; premature before discovery |

### Recommendation

Proceed with **Option 2: governed integration pilot**, subject to the policy
and procurement gates below. It offers the strongest learning-to-risk ratio:
it tests actual user tasks and data controls without treating a product purchase
as the problem definition. The pilot should end with an explicit GO, REVISE, or
STOP decision and a documented basis—not an automatic expansion.

## Stakeholder Engagement Plan

| Engagement | Participants | Question to resolve | Output |
|---|---|---|---|
| Sponsor and service-owner interviews | Executive sponsor, service owner, Finance | What service outcome, risk, and decision are in scope? | Agreed problem statement, decision rights, success measures |
| Current-state workshop | Frontline users, GIS, asset management, reporting, records | Where are records created, corrected, approved, duplicated, and consumed? | Current-state map, pain points, control gaps |
| Data-ownership workshop | System owners, GIS, Finance, privacy/security | Which system owns each key, attribute, geometry, status, and financial field? | Approved ownership matrix and data contract |
| Future-state and option workshop | Users, support, architecture, procurement | What must change, what must remain, and what should be bought versus configured? | Future-state map, requirements, option assumptions |
| Scenario-based vendor demonstrations | Shortlisted suppliers and evaluation team | Can the solution complete the organisation's own priority scenarios? | Individually scored evidence, clarification log |
| UAT and accessibility sessions | Representative users, including assistive-technology needs where applicable | Can each role complete critical tasks safely and efficiently? | UAT results, defects, accessibility findings, release recommendation |
| Decision briefing | Sponsor, leadership, and—where governance requires—Council | What decision is required, what evidence supports it, and what residual risk remains? | Plain-language recommendation and recorded decision |

Participation, dissenting views, decisions, and actions would be documented.
Workshops would not be treated as approval unless the authorised owner records
that approval against the agreed criteria.

## Procurement and Vendor Evaluation

### Mandatory Gates

A response that fails a mandatory requirement would not advance merely because
it scores well elsewhere. Mandatory gates should be confirmed with Legal,
Procurement, Privacy, Security, Accessibility, Records, and service owners and
may include:

- compliance with the organisation's procurement authority and evaluation
  process;
- privacy and security evidence, including identity, logging, breach handling,
  subprocessors, and data-location requirements;
- accessibility conformance evidence and remediation commitments;
- retention, legal hold, audit history, and defensible disposition;
- export of records, configuration, metadata, and audit evidence in usable
  formats without punitive exit barriers;
- open, documented interfaces for required GIS, asset, identity, and BI flows;
- segregation of duties for material approvals; and
- acceptance of scenario-based testing, reference checks, and contractually
  defined service levels.

### Weighted Evaluation Matrix

Weights are proposed for workshop validation before a solicitation is issued.
Each evaluator should score independently against published anchors before the
team moderates differences. Procurement records should preserve the original
scores, rationale, conflicts, clarifications, and consensus result.

| Criterion | Weight | Evidence requested |
|---|---:|---|
| Functional and user-task fit | 20% | Response mapped to numbered requirements; scripted demonstration using supplied scenarios |
| Integration and open standards | 15% | API and event model; GIS formats/services; identity integration; documented limits |
| Privacy, security, and data governance | 15% | Architecture, controls, assurance reports, data flow, incident and subprocessor terms |
| Accessibility and usability | 10% | Current conformance report, keyboard/screen-reader demonstration, defect and remediation process |
| Implementation and change approach | 10% | Discovery, configuration, migration, testing, training, adoption, cutover, rollback, and knowledge transfer |
| Support and service management | 10% | Support model, severity definitions, response/restoration targets, escalation, maintenance notice |
| Total cost and commercial transparency | 10% | Five-year cost model, implementation assumptions, usage thresholds, optional charges, price-adjustment terms |
| Portability and exit | 5% | Export formats, configuration handover, deletion certification, transition assistance, exit fees |
| Supplier capability and references | 5% | Comparable complexity, named delivery roles, reference checks, financial and capacity due diligence |
| **Total** | **100%** | |

### Controlled Demonstration Script

Suppliers should demonstrate the same tasks rather than deliver an unrestricted
sales presentation:

1. ingest a small asset and GIS sample with one duplicate key, invalid point,
   orphan feature, missing feature, and lifecycle mismatch;
2. prevent failed records from being published and route each exception to a
   named role;
3. move from map to asset, work, and reporting context without re-keying the
   identifier;
4. show a complete change and approval audit trail;
5. enforce two contrasting access roles and export the resulting access log;
6. recover from a failed interface or approval without silent data loss;
7. export records, configuration, and evidence in documented formats; and
8. complete priority workflows by keyboard and with representative assistive
   technology.

No supplier-authored substitute dataset should replace the deliberate failure
cases, because the point is to test exception behaviour rather than a polished
happy path.

## Policy, Standard, and Procedure Impact Register

The names and authorities below are categories, not assertions about any
specific jurisdiction. Owners must map them to the organisation's current
bylaws, policies, standards, collective agreements, and procedures during
discovery.

| Area to review | Why it may be affected | Evidence or decision required | Accountable role |
|---|---|---|---|
| Procurement and delegated authority | Pilot, subscription, implementation, or consulting commitments may cross approval thresholds | Approved sourcing route, evaluation plan, conflict declarations, award authority | Procurement / Finance |
| Records and information management | Decisions, approvals, GIS updates, flow logs, and training evidence may be official records | Record classes, retention, legal hold, versioning, disposition, system of record | Records owner |
| Privacy | Asset or location workflows may include personal, employee, tenant, or sensitive infrastructure data | Data inventory, lawful purpose, minimisation, access, disclosure, retention, privacy assessment | Privacy officer |
| Cybersecurity and identity | New connectors, service accounts, external suppliers, and mobile access expand the control surface | Threat/risk review, least privilege, MFA, logging, credential and incident process | Security owner |
| Accessibility | Staff and public-facing outputs must be usable by people with disabilities | Applicable standard, test plan, conformance evidence, remediation owner | Accessibility lead |
| Asset and GIS standards | Keys, coordinate reference systems, positional accuracy, lifecycle states, and publishing rules must be consistent | Approved data dictionary, CRS/transformation record, quality thresholds, publication authority | Asset / GIS owner |
| Open data and public release | Internal attributes or precise locations may not be suitable for public publication | Release classification, redaction/generalisation rule, approval record, update cadence | Communications / data owner |
| Financial controls | Asset values, cost centres, projects, subscriptions, and benefits must reconcile | Financial mapping, budget authority, total-cost baseline, benefits owner | Finance |
| Service continuity | Migration, integration failure, or vendor outage may interrupt operational reporting or field work | Business-impact analysis, fallback, backup, recovery, rollback, support ownership | Service owner / IT |
| Change, training, and labour impacts | Roles, approvals, workload, monitoring, and required skills may change | Impact assessment, consultation obligations, training plan, readiness evidence | HR / change lead |

Any required bylaw change, public notice, consultation, legal review, or Council
approval would be recorded as a dependency rather than assumed within the
project team's authority.

## Delivery and Decision Plan

| Stage | Illustrative duration | Exit evidence | Decision |
|---|---:|---|---|
| Mobilise | 2 weeks | Sponsor, scope, RACI, engagement plan, RAID, records location | Start / revise |
| Discover and define | 4 weeks | Current state, data ownership, requirements, policy impacts, baseline measures | Approve pilot design |
| Configure and integrate pilot | 6 weeks | Working limited-scope flow, security model, support draft, migrated sample | Ready for test |
| Validate | 2 weeks | Functional, data, privacy/security, accessibility, performance, UAT, rollback evidence | GO / revise / stop |
| Pilot operation and adoption | 4 weeks | Usage, task success, exception resolution, support demand, user feedback | Sustain / improve / stop |
| Production recommendation | 2 weeks | Options, total-cost range, procurement path, benefits, residual risks, implementation plan | Approve next phase or close |

Durations are hypotheses, not commitments. The approved plan would identify
dependencies, resource capacity, blackout periods, decision dates, and schedule
risk. Weekly status would report milestone variance, RAID changes, decisions
required, budget position where available, and next-period work.

## Success and Guardrail Measures

| Measure | Pilot target | Guardrail |
|---|---:|---|
| Published records passing identity, geometry, lifecycle, and ownership rules | 100% | Failed records remain visible in an owned exception queue |
| Priority requirements traced to owner, acceptance criterion, and test | 100% | Scope changes require a recorded decision |
| Critical user scenarios passed before release | 100% | No default acceptance when evidence is missing |
| Required role and accessibility tests completed | 100% | Unresolved critical barriers block release |
| Exceptions resolved within agreed service target | Baseline then target after discovery | Age and ownership remain visible; closure requires evidence |
| Required training completed by pilot roles | At least 90% before launch | Critical-role gaps trigger delay or approved mitigation |
| Pilot users completing priority tasks without spreadsheet re-keying | Baseline plus agreed improvement | User feedback and error rates are reported with task completion |
| Unplanned interruption to the incumbent service | 0 critical incidents | Rollback remains available through the agreed validation period |

## Briefing Design by Audience

The evidence should stay consistent while the emphasis changes:

- **Operational staff:** task changes, exception handling, support, training,
  fallback, and what will not change.
- **Technical and control owners:** architecture, data ownership, security,
  privacy, accessibility, records, test evidence, and recovery.
- **Leadership:** service outcome, cost range, capacity, options, delivery
  confidence, unresolved risks, and decisions needed.
- **Council or governing body, where required:** public value, service impact,
  financial and procurement authority, privacy/accessibility considerations,
  options, recommendation, material risk, and the precise approval requested.

A Council-style brief should use plain language, separate confirmed facts from
assumptions, avoid technical implementation detail unless it changes risk or
cost, and make clear which decisions remain with staff under delegated
authority.

## Recommendation Conditions

The pilot recommendation remains valid only if:

1. accountable owners approve the problem, scope, requirements, and success
   measures;
2. Procurement confirms the sourcing approach before supplier engagement;
3. Privacy, Security, Accessibility, Records, Finance, and Legal reviews are
   completed at the gates appropriate to the jurisdiction;
4. authoritative data ownership and exception accountability are explicit;
5. release cannot proceed without required acceptance evidence; and
6. the final recommendation reports total cost, limitations, dissenting
   evidence, and residual risk as clearly as expected benefit.

## Related Evidence

- [Business Analysis Delivery Pack](README.md)
- [Project Charter](PROJECT_CHARTER.md)
- [Process and Requirements](PROCESS_AND_REQUIREMENTS.md)
- [Stakeholder and RACI](STAKEHOLDER_AND_RACI.md)
- [RAID Register](RAID_REGISTER.md)
- [Status Report](STATUS_REPORT.md)
- [Change and Adoption Plan](CHANGE_AND_ADOPTION_PLAN.md)
- [Microsoft Modern Workplace Delivery Blueprint](MODERN_WORKPLACE_BLUEPRINT.md)
- [GIS Integration Requirements](GIS_INTEGRATION_REQUIREMENTS.md)
- [Runnable GIS asset acceptance gate](../../examples/gis_asset_integration/)
- [Runnable asset lifecycle, risk, renewal, and capital-scenario evidence](../../examples/asset_management/)
