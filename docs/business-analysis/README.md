# Business Analysis Delivery Pack

This pack documents the business-analysis and project-delivery work around the
synthetic 140-artifact migration programme in this repository. It turns the
technical proof into a traceable change story: why the change is needed, who
must participate, what the solution must do, how decisions are controlled, and
how people move to the new service safely.

The programme, organisations, roles, schedules, and registers below are a
portfolio simulation built from the repository's generated migration dataset.
They do not claim a completed client engagement or a deployed Microsoft 365
tenant. The runnable pipeline, Power BI project, validation evidence, tests,
and cutover runbook remain the implemented parts of the repository.

## Decision Trail

| Stage | Question answered | Evidence |
|---|---|---|
| Discover | What is changing, why, and for whom? | [Project charter](PROJECT_CHARTER.md) and [stakeholder map](STAKEHOLDER_AND_RACI.md) |
| Define | What must the future service do? | [Process and requirements](PROCESS_AND_REQUIREMENTS.md) |
| Decide | Who owns decisions, risks, and exceptions? | [RACI](STAKEHOLDER_AND_RACI.md) and [RAID register](RAID_REGISTER.md) |
| Deliver | How is the work sequenced and controlled? | [Project charter](PROJECT_CHARTER.md), [status report](STATUS_REPORT.md), and the existing [cutover runbook](../cutover_runbook.md) |
| Adopt | How are affected teams prepared and supported? | [Change and adoption plan](CHANGE_AND_ADOPTION_PLAN.md) |
| Operate | How could the work be governed in Microsoft 365? | [Modern Workplace blueprint](MODERN_WORKPLACE_BLUEPRINT.md) |
| Integrate | How should spatial and asset data connect safely? | [GIS integration requirements](GIS_INTEGRATION_REQUIREMENTS.md) |
| Manage assets | How do condition, criticality, lifecycle, renewal need, inspections, data confidence, and affordability become a controlled work programme? | [Runnable asset-management evidence](../../examples/asset_management/README.md) |
| Build the capital case | Which funding posture should proceed, what can be delivered and afforded, what changes under stress, and which gates still block authority to spend? | [Asset capital programme business case](ASSET_CAPITAL_PROGRAM_BUSINESS_CASE.md) and [live decision board](https://kush-asset-management-decision-board.streamlit.app/) |
| Govern | How would a public body brief decision-makers, evaluate suppliers, and check policy impacts? | [Public-sector decision and procurement brief](PUBLIC_SECTOR_DECISION_AND_PROCUREMENT_BRIEF.md) |

## Scope Boundary

This pack demonstrates planning, facilitation design, requirements
traceability, project controls, change management, and executive reporting.
It does not add fictional production outcomes. Targets are labelled as
targets, role owners are role names rather than invented people, and the
Modern Workplace document is explicitly a design blueprint rather than a
deployment claim.

The GIS integration document is also a design artifact. It demonstrates
requirements and control thinking around spatial data without claiming
production GIS administration or municipal delivery experience.

The asset-management extension is implemented against a 96-record synthetic
portfolio and tested in CI. Its condition, criticality, renewal, risk, work
programme, and capital-affordability outputs are scenario evidence—not an
engineering condition assessment or an approved municipal capital plan.

The capital-programme business case adds three decision postures, a constrained
multi-year plan, escalation/contingency/discount and funding assumptions,
sensitivity analysis, owned programme risks, benefits measures, delivery gates,
and an exportable committee pack. Its preferred posture is explicitly
conditional and does not imply authority to spend.

The public-sector decision and procurement brief is a jurisdiction-neutral
portfolio scenario. It demonstrates decision writing, option and vendor
evaluation, policy-impact analysis, and Council-style briefing structure; it
does not claim a completed public procurement or municipal employment.
