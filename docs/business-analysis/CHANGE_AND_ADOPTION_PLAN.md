# Change and Adoption Plan

## Change Objective

Move users and support teams from a familiar legacy reporting process to a
governed Fabric service without losing trust, deadlines, access, or the ability
to explain a number. The behavioural change is as important as the platform:
issues move from informal email reconciliation into an owned, traceable
support and decision process.

## Impact Assessment

| Audience | Current experience | Future experience | Main concern | Required support |
|---|---|---|---|---|
| Report consumers | Receive legacy report or workbook | Use repointed report with the same approved definitions | Will my number or deadline change? | Comparison evidence, concise briefing, support route |
| Business owners | Approve changes informally | Approve requirements, UAT, and retirement in a recorded trail | Is approval becoming bureaucracy? | Clear decision points and delegated authority |
| Analysts | Reconcile after publication | Review validation and exceptions before GO | Can I investigate differences quickly? | Traceability guide and exception workflow |
| Technical team | Support two platforms during migration | Operate Fabric service with monitored controls | How long must dual running continue? | Wave plan, exit criteria, runbook |
| Service desk | Escalate legacy issues to specialists | Triage known issues and route platform incidents | What changed and who owns it? | Knowledge article, scripts, escalation matrix |

## Communications

| Timing | Audience | Purpose | Channel | Owner | Evidence |
|---|---|---|---|---|---|
| Wave initiation | Owners and delivery team | Confirm scope, decisions, and dates | Kickoff and summary | Programme manager | Attendance and decision log |
| Before requirements baseline | Users and owners | Validate needs and exceptions | Workshop | Business analyst | Approved outputs |
| Two weeks before UAT | Testers | Confirm scenarios, access, and schedule | Teams meeting and guide | Business analyst | Tester readiness |
| Five working days before cutover | All affected users | Explain timing, expected continuity, support, and rollback | Email and Teams post | Change lead | Distribution record |
| GO or NO-GO | Owners and support | Record decision and conditions | Decision meeting | Programme manager | Approved decision |
| Hypercare days 1, 3, and 5 | Users and support | Share known issues and adoption signals | Brief status update | Service owner | Status record |

## Training and Enablement

- A 20-minute consumer briefing covers what is changing, what is not changing,
  where definitions live, and how to report a problem.
- A role-based analyst session covers filters, reconciliation evidence,
  validation status, and known limitations.
- A service-desk session covers symptoms, first checks, priority, ownership,
  and escalation.
- One-page job aids are versioned with the release candidate.
- Recorded material supplements rather than replaces a live question period.

## Readiness Checklist

- [ ] Business owner and delegated approver confirmed
- [ ] Impacted audiences and critical deadlines confirmed
- [ ] UAT testers have access and representative scenarios
- [ ] Communication and training material match the release candidate
- [ ] Service-desk article and escalation matrix approved
- [ ] Open issues and workarounds published
- [ ] Rollback owner, trigger, and communication text ready
- [ ] No open critical risk or defect

## Adoption Measures

| Measure | Target | Interpretation and action |
|---|---:|---|
| Required-user preparation completed | At least 90% | Block GO if a critical role is unsupported. |
| UAT participation | 100% of critical scenarios | Move the decision if critical coverage is missing. |
| Report delivery on time | 100% during hypercare | Invoke incident and rollback criteria if missed. |
| Access-related incidents | 0 critical | Review role mapping immediately. |
| Repeat how-to contacts after week 2 | Downward trend | Add or simplify guidance where contacts cluster. |
| Business-owner acceptance | 100% before retirement | Keep legacy available until recorded. |

## Resistance and Feedback

- Treat resistance as information about risk, workload, or loss of control.
- Record the concern, affected process, evidence needed, owner, and decision.
- Demonstrate legacy and Fabric outputs side by side for trust questions.
- Do not dismiss an exception because it affects few users; determine whether
  those users own a critical deadline.
- Feed recurring support contacts into the backlog and training update.

## Reinforcement

At the end of hypercare, the business owner, service desk, and technical lead
review adoption measures, open issues, lessons, and retirement readiness. The
legacy artifact remains available for the retention period defined in the
[cutover runbook](../cutover_runbook.md).
