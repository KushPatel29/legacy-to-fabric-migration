# Product Backlog and Executable Acceptance Criteria

The [requirements register](PROCESS_AND_REQUIREMENTS.md#requirements-register)
says what the migration must do. This backlog breaks it into user stories a
delivery team can pick up, each with acceptance criteria written as
Given / When / Then. Every criterion marked **runs** names the test in this
repository that executes it on every push, so "accepted" means a green check, not
a signature on a document. Criteria marked **manual** are UAT scenarios or design
targets and say so; none of them is claimed as achieved.

[`tests/test_backlog_traces_to_tests.py`](../../tests/test_backlog_traces_to_tests.py)
fails the build if a cited test is renamed or deleted, if a *Must* requirement in
the register has no story, or if the Jira import file drifts from this page.
[`backlog.csv`](backlog.csv) is the same backlog in Jira's CSV import format
(Issue Type, Summary, Epic, Priority, Labels, Acceptance Criteria). It has not been
loaded into a Jira instance.

Priorities are MoSCoW, taken from the register. The programme and its people are
the synthetic simulation described in the [pack README](README.md).

## Definition of Ready

- The story names its user, the outcome, and the requirement ID it serves.
- Acceptance criteria are testable as written, and each says whether it runs in CI
  or is a manual UAT scenario.
- The data needed to test it exists in the synthetic programme, or the story says
  what is missing.

## Definition of Done

- Every **runs** criterion passes in CI on the main branch.
- Every **manual** criterion has a UAT scenario with an expected result and an owner.
- The traceability test passes, so the story, the register and the code agree.

## Epic E1 — Prove every migrated output before the legacy one is retired

### US-01 · Compare each migrated output row for row
**As** the finance owner, **I want** every migrated report compared row for row with its
legacy output, **so that** I can retire the legacy report without re-checking it by hand.
Requirement: FR-02 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | a parallel run where Fabric matches legacy exactly | the validator runs | the verdict is GO | runs: `tests/test_parallel_run_validation.py::test_clean_parallel_run_is_go` |
| 2 | a Fabric output missing one legacy row | the validator runs | the verdict is NO-GO and names the failing check | runs: `tests/test_parallel_run_validation.py::test_dropped_row_is_nogo` |
| 3 | one value shifted on one row | the validator runs | the verdict is NO-GO | runs: `tests/test_parallel_run_validation.py::test_shifted_value_is_nogo` |
| 4 | two errors that cancel out in the column total | the validator runs | the verdict is still NO-GO | runs: `tests/test_parallel_run_validation.py::test_offsetting_errors_still_caught` |
| 5 | a key present in Fabric but not in legacy | the validator runs | the verdict is NO-GO | runs: `tests/test_parallel_run_validation.py::test_extra_key_is_nogo` |

### US-02 · An empty output never passes
**As** the technical lead, **I want** an empty extract never to count as a match, **so that**
a broken load cannot be signed off because both sides were blank.
Requirement: FR-03 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | both legacy and Fabric outputs are empty | the validator runs | the verdict is not GO | runs: `tests/test_validator_edge_cases.py::test_two_empty_outputs_are_not_a_go` |
| 2 | only one side is empty | the validator runs | the verdict is not GO | runs: `tests/test_validator_edge_cases.py::test_one_side_empty_is_not_a_go` |
| 3 | a duplicated key on one side | the validator runs | the duplicate is caught | runs: `tests/test_validator_edge_cases.py::test_duplicate_key_on_one_side_is_caught` |

### US-03 · Same numbers, whatever the formatting
**As** the metric owner, **I want** formatting and row-order differences ignored but any real
difference caught to the cent, **so that** users keep exactly the approved numbers and the
gate does not cry wolf.
Requirement: BR-03 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | the same values stored as different numeric types | checksums are compared | they match | runs: `tests/test_parallel_run_validation.py::test_checksum_ignores_dtype_formatting` |
| 2 | the same rows in a different order | the validator runs | the verdict is GO | runs: `tests/test_validator_edge_cases.py::test_row_order_does_not_matter` |
| 3 | integer and float representations of one amount | the validator runs | they agree | runs: `tests/test_validator_edge_cases.py::test_integer_and_float_representations_agree` |
| 4 | a sub-cent rounding difference | the validator runs | the gate does not fail | runs: `tests/test_validator_edge_cases.py::test_sub_cent_rounding_does_not_fail_the_gate` |
| 5 | a difference of one cent | the validator runs | the gate fails | runs: `tests/test_validator_edge_cases.py::test_the_gate_is_cent_exact_not_merely_within_a_cent` |
| 6 | a quantity that drifts while amounts match | the validator runs | the drift is caught | runs: `tests/test_validator_edge_cases.py::test_quantity_drift_alone_is_caught` |

### US-04 · GO means every check passed
**As** the business owner, **I want** GO only when every check passes, with totals reported per
column, **so that** one green check cannot hide a red one.
Requirement: FR-03 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | any single check fails | the verdict is formed | it is NO-GO | runs: `tests/test_validator_edge_cases.py::test_verdict_is_conjunctive` |
| 2 | a completed run | the result is reported | control totals appear per column | runs: `tests/test_validator_edge_cases.py::test_control_totals_are_reported_per_column` |
| 3 | a NO-GO in a scheduled wave | retirement is requested | it is refused until a GO is recorded | manual: UAT scenario owned by the technical lead |

## Epic E2 — Run the programme from one register

### US-05 · One record per artifact
**As** the programme manager, **I want** every artifact to carry its status, wave, owner,
planned and actual effort, **so that** progress reports show what the data supports.
Requirement: FR-01 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | the generated programme register | it is loaded | every artifact links to a valid wave, owner and blocker | runs: `tests/test_migration_program_data.py::test_referential_integrity` |
| 2 | any artifact | its status is read | it is one of the allowed statuses | runs: `tests/test_migration_program_data.py::test_statuses_valid` |
| 3 | an artifact marked Done | its effort is read | actual effort is recorded | runs: `tests/test_migration_program_data.py::test_done_artifacts_have_actuals` |

### US-06 · Done means proven
**As** the programme manager, **I want** an artifact marked Done only after a GO, **so that**
"done" in a status report means "validated", not "deployed".
Requirement: FR-03 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | an artifact marked Done | its validation history is read | its last verdict is GO | runs: `tests/test_migration_program_data.py::test_done_artifacts_end_on_go` |
| 2 | any NO-GO verdict | its reason is read | the reason matches the failing check | runs: `tests/test_migration_program_data.py::test_verdict_reason_consistency` |

## Epic E3 — A command centre people can rely on

### US-07 · Every visual can be read without seeing it
**As** a report user who relies on a screen reader, **I want** every visual to carry alt text
that describes that visual, **so that** I get the same information as everyone else.
Requirement: proposed NFR-04, accessibility (not yet in the register) · Priority: Should

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | any visual in the Power BI project | the report is built | it has alt text | runs: `tests/test_every_visual_has_alt_text.py::test_every_visual_has_alt_text` |
| 2 | a visual's alt text | it is read | it describes that visual, not a generic label | runs: `tests/test_every_visual_has_alt_text.py::test_alt_text_describes_this_visual` |

### US-08 · Filters say what they cannot filter
**As** a report user, **I want** a visual that a slicer cannot reach to say so, **so that** I do
not read an unfiltered number as a filtered one.
Requirement: FR-01 · Priority: Should

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | a slicer and a visual it cannot filter | the page is built | the visual states its scope | runs: `tests/test_slicer_scope_is_visible.py::test_every_visual_a_slicer_cannot_reach_says_so` |

### US-09 · Dates cover the whole programme
**As** a report user, **I want** the calendar to cover every month the programme touches,
**so that** no wave silently falls outside a date filter.
Requirement: FR-01 · Priority: Should

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | the programme's dated files | the calendar is derived | every joined month lies inside it | runs: `tests/test_the_calendar_covers_the_programme.py::test_every_joined_month_lies_inside_the_span_the_calendar_derives` |
| 2 | the calendar definition | it is read | it is not pinned to a literal date | runs: `tests/test_the_calendar_covers_the_programme.py::test_the_calendar_is_not_pinned_to_a_literal_date` |

## Epic E4 — Release with evidence

### US-10 · Tamper-evident release evidence
**As** the release reviewer, **I want** the release packet's evidence hashed and verifiable,
**so that** what was approved is provably what was tested.
Requirement: NFR-03 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | the release packet | it is checked | every required evidence file is present and hashed | runs: `tests/test_production_readiness.py::test_required_evidence_is_present_and_integrity_hashed` |
| 2 | an edited evidence file | the digest is verified | the tampering is detected | runs: `tests/test_production_readiness.py::test_packet_digest_verifies_and_detects_tampering` |

### US-11 · Approve only what was reviewed
**As** the release reviewer, **I want** the packet to approve only the public synthetic demo and
keep authentication, telemetry and live Fabric open, **so that** no one reads a demo approval as
a production one.
Requirement: NFR-01 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | the release packet | its scope is read | it approves only the public synthetic demo | runs: `tests/test_production_readiness.py::test_release_packet_approves_only_the_public_synthetic_demo` |
| 2 | the release packet | open reviews are listed | authentication, telemetry and live Fabric are still open | runs: `tests/test_production_readiness.py::test_packet_keeps_auth_telemetry_and_live_fabric_as_open_reviews` |

## Epic E5 — People move to the new service safely

### US-12 · Every user group hears before its wave
**As** the change lead, **I want** each affected user group to receive role-specific
communication before its wave, **so that** nobody meets the new report on cutover morning.
Requirement: CHG-01 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | a scheduled wave | the communication register is checked a week before | every affected group shows a delivered message | manual: target in the [change and adoption plan](CHANGE_AND_ADOPTION_PLAN.md), not claimed as achieved |

### US-13 · Cutover can be undone in time
**As** the technical lead, **I want** a rehearsed rollback that completes inside the recovery
window, **so that** a failed cutover costs hours, not a month-end.
Requirement: NFR-02 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | a rehearsal cutover that fails | rollback is run from the [cutover runbook](../cutover_runbook.md) | legacy service resumes inside the agreed window | manual: rehearsal scenario owned by the technical lead |

### US-14 · Every artifact has an owner before it moves
**As** the business owner, **I want** each artifact's owner, purpose, criticality and
consumers recorded before it is scheduled, **so that** someone can accept or refuse it.
Requirement: BR-01 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | the artifact inventory | completeness is reported | 100% of artifacts carry owner, purpose, criticality and consumers | manual: designed control in this pack; not implemented as a production records system |

### US-15 · Month-end never goes dark
**As** the finance owner, **I want** waves scheduled around a blackout calendar, **so that**
month-end and statutory outputs stay available throughout.
Requirement: BR-02 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | the approved blackout calendar | a wave is scheduled | no cutover falls inside a blackout window | manual: UAT scenario owned by the finance owner |

### US-16 · Users are ready before GO
**As** the business owner, **I want** required users and service-desk analysts to finish their
preparation before a wave goes live, **so that** support is not learning the service from the
first ticket.
Requirement: CHG-02 · Priority: Must

| # | Given | When | Then | Status |
|---|---|---|---|---|
| 1 | a wave's readiness review | completion is checked | at least 90% of required users are prepared and no critical role is unsupported | manual: target in the [change and adoption plan](CHANGE_AND_ADOPTION_PLAN.md), not claimed as achieved |
