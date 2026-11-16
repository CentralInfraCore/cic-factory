# Protect the measuring-tool pin file (and its surfaces) from the pull request it verifies

**Context.** PR-06 of #169 (CIC_Relay #191) pins the measuring tools in `.measurement-tools.json` and makes every measuring job fail closed on a different, missing, unknown or unpinned tool (`scripts/quality_gate.py check-tools --surface …`, `object_model.py verify --mode quality`).

**The gap.** The pin file, and the `surfaces` in it that say which tools a job must declare, live in the same tree the gates read. A pull request that is under verification can edit them in the same change that edits the workflow or the tool setup, so the PR can define its own acceptance reference. Today only `scripts/gremlins_gate.py` and `.mutation-baseline.json` are protected from the base commit by `baseline-guard`; the pin file is not. A change of the file is gate-logic (the planner escalates to FULL), which is a cost, not a protection against a manipulating PR.

This is a trust-boundary problem, not a style point: a check whose reference the checked change can rewrite proves only that the change is consistent with itself.

**Acceptance criteria** (as set by the PR-06 review):
1. The PR under verification cannot unilaterally change the authentic reference of the check (the pins and the surfaces are read from the base commit, or an equivalent that the PR cannot write).
2. An intended pin update has a separate, owner-approved path (so a legitimate tool bump stays possible and visible).
3. The rejection of a manipulation is shown by a negative proof PR (a deliberately defective, non-mergeable PR that edits the pin file together with the tool setup and must be rejected).
4. The result of the check records the reference commit and the digest it used.

**Out of scope here / not decided:** whether this is needed for the PR-06 quality-policy contract or is its own next step is for the PR-06 review to decide; this issue does not change PR-06. No new threshold, no toolchain change. Related, separate: `cargo-mutants` and `cargo-llvm-cov` are installed without a pin (`taiki-e/install-action`), so a new release turns the gates red until the pin is updated by hand.

**Evidence of the current behaviour:** PR-06 report `jobs/relay-ci-parity-06-trust-boundary-ffi-negative-tests/output/pr06-report.md` (section 3, limits) in cic-factory #64; proof PR #193 shows that a pin that differs from the setup is rejected, which is the opposite case (the PR does not touch the setup).

