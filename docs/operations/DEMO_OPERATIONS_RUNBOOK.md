# Runbook: release and recover the public asset decision demonstration

**Owner:** Repository maintainer | **Frequency:** Every release / incident  
**Last updated:** 18 September 2026 | **Last run:** CI on the current commit

## Purpose

Rebuild, verify, publish and—if necessary—roll back the public synthetic asset
and migration demonstration. For an actual SSIS-to-Fabric cutover, use the
separate [cutover runbook](../cutover_runbook.md).

## Prerequisites

- [ ] Python 3.12 and Git are available.
- [ ] Worktree is clean and the intended branch is checked out.
- [ ] No real, personal, employer or municipal data is present.
- [ ] Direct dependencies remain exactly pinned in both requirements files.

## Procedure

### Step 1: Rebuild deterministic evidence

```bash
python data_generator/generate_source_data.py
python validation/build_local_reference_outputs.py
python validation/parallel_run_validation.py
python examples/gis_asset_integration/reconcile_gis_assets.py
python examples/asset_management/build_asset_management_case.py
```

**Expected result:** parallel validation returns GO; GIS and asset outputs are
regenerated without hidden exceptions.  
**If it fails:** do not publish. Compare the changed source/output, identify
whether the pipeline or validator is wrong, and preserve the NO-GO evidence.

### Step 2: Build the production-readiness evidence

```bash
python governance/build_production_evidence.py
```

**Expected result:** `APPROVE PUBLIC DEMONSTRATION`, `NOT AUTHORIZED` for
production, 8 PASS / 3 REVIEW / 0 BLOCK, plus packet, memo and SBOM in `output/`.
  
**If it fails:** treat a missing evidence file, unpinned dependency, compile
error or decision-engine latency breach as a release block. Do not edit the
packet by hand.

### Step 3: Run the complete acceptance suite

```bash
python -m pytest tests/ -q
```

**Expected result:** every collected test passes and the count matches the
README badge.  
**If it fails:** fix the implementation or documented claim; never reduce the
assertion merely to restore green CI.

### Step 4: Review and publish

Review these files before merge:

- `output/production_readiness_memo.md`
- `output/production_readiness_packet.json`
- `output/sbom.cdx.json`
- changed asset/GIS/migration evidence

Merge only after CI repeats Steps 1–3. The public app is a best-effort host; the
portfolio screenshots and repository evidence are the static fallback.

## Verification

- [ ] CI is green on the published commit.
- [ ] Live app opens and states the synthetic/non-approval boundary.
- [ ] One default scenario completes and its downloadable pack opens.
- [ ] Static fallback images and repository evidence remain accessible.
- [ ] Production readiness remains `NOT AUTHORIZED` until PRD-09–11 are closed.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| App is sleeping or slow on first visit | free-host cold start | wait once; use static evidence if the second attempt fails |
| Release packet returns HOLD | one executable gate is blocked | inspect the named gate and its evidence; revert or repair before publishing |
| Parallel validation returns NO-GO | real transformation drift or validator normalization issue | compare row counts/totals/checksums and follow `docs/cutover_runbook.md` |
| Asset count or dollar total changes | source generator or decision rule changed | review the diff and update claims only after acceptance evidence passes |
| SBOM builder rejects a requirement | dependency is unpinned or conflicts across files | choose and test one exact version; do not permit a floating production dependency |

## Rollback

1. Identify the last green commit and its matching public evidence.
2. Revert the release commit through normal version control.
3. Re-run the evidence builders and complete suite.
4. Confirm the public app and static fallback show the restored release.
5. Record cause, impact, detection gap and corrective control before retrying.

For a real reporting cutover, keep the legacy job disabled—not deleted—until
the agreed retention window completes; the exact system rollback is documented
in `docs/cutover_runbook.md`.

## Escalation

| Situation | Contact | Method |
|---|---|---|
| Public synthetic demo failure | repository maintainer | open a repository issue with commit, time and failing gate |
| Suspected credential or sensitive-data exposure | repository owner | stop publication, rotate affected credentials, remove access and preserve incident evidence |
| Production/municipal adoption request | accountable data owner, security, privacy, asset lead and platform owner | formal design and approval process; this demo is not the production authority |

## History

| Date | Run by | Notes |
|---|---|---|
| 18 September 2026 | Repository maintainer | Initial executable production-floor release |
