# Microsoft Modern Workplace Delivery Blueprint

## Evidence Boundary

This is a solution blueprint for managing the simulated migration programme
with Microsoft Teams, SharePoint, and Power Automate. It has not been deployed
to a production Microsoft 365 tenant, so it demonstrates implementation
planning rather than production administration experience.

## Collaboration Design

### Teams

Create one programme team with channels aligned to durable work rather than
temporary meetings:

- General and governance
- Requirements and decisions
- Build and validation
- Change, training, and support
- One private channel only where restricted commercial or security material
  genuinely requires separate membership

Channel tabs point to filtered SharePoint views rather than duplicate files.
Decisions are recorded in the decision list; chat is not the system of record.

### SharePoint

| Component | Purpose | Key fields or controls |
|---|---|---|
| Migration inventory list | One record per artifact | Owner, criticality, wave, status, target, dependencies |
| Requirements list | Trace needs to evidence | ID, statement, priority, owner, acceptance criteria, test, status |
| RAID list | Manage risks, assumptions, issues, dependencies | Type, probability, impact, trigger, response, owner, due date |
| Decision list | Preserve approvals and conditions | Decision, options, recommendation, approver, date, conditions |
| Change and training list | Track readiness by audience | Audience, impact, communication, training, completion, evidence |
| Controlled document library | Store approved baselines and runbooks | Content type, owner, status, version, retention label |

Use list-level views for each wave and audience. Avoid item-level permissions
unless required because they become difficult to audit and support at scale.

## Power Automate Flows

| Flow | Trigger | Main actions | Failure path |
|---|---|---|---|
| High-risk alert | RAID item created or raised to Critical | Notify owner and programme manager, create acknowledgement task, log timestamp | Retry transient failure; escalate if no acknowledgement within SLA |
| Requirement approval | Requirement moves to Ready for approval | Send approval to business owner, lock approved baseline fields, record outcome | Return rejected item with comment; never treat timeout as approval |
| Weekly status digest | Scheduled weekly | Summarise milestones, open high risks, overdue actions, and decisions required | Publish a visible failed-run notice to the programme owner |
| Cutover readiness | All mandatory checklist items marked complete | Request GO or NO-GO decision and write conditions to decision list | Block request if evidence is missing; no default GO |
| Training reminder | Required completion remains open before cutover | Send role-based reminder and escalate critical-role gaps | Stop after cutover cancellation; prevent duplicate reminders |

## Governance and Security

- Use named owners and a service account or managed connection approved for
  production flows; do not bind critical automation to one employee account.
- Separate author, approver, and administrator where the decision is material.
- Apply least privilege to sites, lists, connectors, and report workspaces.
- Retain version history and approved baselines.
- Log flow run ID, item ID, decision, actor, timestamp, and failure reason.
- Define data classification before placing sensitive information in Teams or
  SharePoint.
- Test with non-sensitive data and a pilot wave before broader rollout.

## Acceptance Tests

1. A critical risk notifies the correct roles and records acknowledgement.
2. A rejected requirement cannot be marked approved by a downstream flow.
3. A cutover request cannot start with a missing mandatory evidence link.
4. A failed approval or connector call produces a visible, owned exception.
5. A user without permission cannot read restricted decision evidence.
6. A departed owner can be replaced without recreating the programme history.
7. A scheduled digest reconciles its counts to the source lists.

## Implementation Sequence

1. Confirm records, privacy, security, and retention requirements.
2. Prototype lists and views with one migration wave.
3. Validate terminology and ownership with users.
4. Build flows in a development environment with failure-path tests.
5. Complete security, accessibility, and support reviews.
6. Pilot, measure, revise, and then scale.
