# Project Charter

## Legacy Reporting Modernisation Programme

**Status:** Portfolio simulation for approval

**Sponsor:** Executive sponsor, Finance and Corporate Services

**Business owner:** Director, Enterprise Systems

**Delivery lead:** Programme manager

**Business analysis lead:** Business analyst

**Implementation:** Data platform and reporting teams

## Purpose

Move a synthetic estate of 140 SSIS packages, SSRS reports, stored-procedure
loads, SQL Agent jobs, and Access or Excel feeds to governed Microsoft Fabric
services without interrupting business-critical reporting or changing an
approved metric without its owner knowing.

The programme exists because a technical migration is also an organisational
change. Reports have owners, consumers, deadlines, controls, and undocumented
dependencies. A successful cutover must preserve those obligations as well as
the data.

## Problem Statement

The current estate has no single inventory that connects each artifact to its
business owner, criticality, downstream consumers, migration wave, acceptance
criteria, and retirement decision. This makes scope, sequencing, risk, and
status difficult to govern. A technically correct replacement could still
fail if a month-end dependency is missed, access changes, training arrives
late, or a legacy process is retired before its consumers sign off.

## Objectives

1. Establish one approved inventory with an owner, criticality, complexity,
   dependencies, and target landing zone for every artifact.
2. Agree requirements and acceptance criteria with business and technical
   stakeholders before development begins.
3. Sequence the estate into risk-based migration waves.
4. run legacy and Fabric outputs in parallel and require a recorded GO verdict
   before retirement.
5. Prepare users, support teams, and process owners before each cutover.
6. Leave a searchable decision, risk, issue, validation, and approval trail.

## In Scope

- Discovery and ownership of the generated 140-artifact estate
- Stakeholder engagement and requirements management
- Current-state and future-state workflow definition
- Wave planning and dependency management
- Fabric implementation and report repointing
- Data, security, functional, and user-acceptance testing
- Parallel-run validation, cutover, rollback, and retirement
- Communications, training, adoption monitoring, and transition to support

## Out of Scope

- Redefining business KPIs without a separate approved change
- Replacing source ERP or finance applications
- Building unrelated net-new dashboards
- Selecting a production tenant, licensing model, or systems integrator
- Claiming that the simulated schedule or targets were achieved in production

## Success Measures

| Measure | Target | Evidence source |
|---|---:|---|
| Estate with named business owner and criticality | 100% | Migration inventory |
| Requirements with acceptance criteria and owner | 100% | Requirements register |
| Tier 1 artifacts with consecutive clean parallel runs | 3 | Validation log |
| Critical cutovers completed without Sev 1 incident | 100% | Incident and cutover logs |
| Required users completing role-based preparation | At least 90% | Training register |
| Business-owner sign-off before retirement | 100% | Decision log |
| Open critical risks at GO or NO-GO meeting | 0 | RAID register |

## Delivery Approach

| Phase | Primary output | Exit decision |
|---|---|---|
| Discover | Inventory, stakeholder map, current-state process | Scope accepted |
| Define | Requirements, acceptance criteria, future-state process | Requirements baseline approved |
| Plan | Wave plan, schedule, RACI, RAID, change impacts | Wave authorised |
| Build | Fabric artifact and updated support documentation | Ready for test |
| Validate | Functional, security, UAT, and parallel-run results | GO or NO-GO |
| Transition | Cutover, training, hypercare, rollback readiness | Service accepted |
| Close | Legacy retirement and lessons learned | Closure approved |

## Governance

- The executive sponsor approves scope, funding, and unresolved high-impact
  decisions.
- The business owner approves requirements, acceptance criteria, and the final
  retirement decision.
- The programme manager owns delivery cadence, schedule, dependencies, and
  escalation.
- The business analyst owns traceability, workshop outputs, decisions, and
  change impacts.
- Technical leads own solution quality and remediation.
- No artifact retires without the evidence defined in the
  [cutover runbook](../cutover_runbook.md).

## Constraints

- Month-end and statutory reporting windows cannot be interrupted.
- Some legacy consumers may be undocumented until discovery.
- Business owners have limited capacity for workshops and UAT.
- Access controls must be preserved or strengthened during migration.
- Rollback must remain available for one complete reporting cycle.
