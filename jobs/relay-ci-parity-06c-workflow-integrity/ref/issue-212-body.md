# Enforce the integrity of the measuring workflows against the pull request under verification (follow-up of #195, proof #207)

**Context.** #195 / PR #201 protects the *reference* of the measuring-tool check: the pins, surfaces and approvers are read from the base branch, the checking script runs from the base, a changed pin file needs an approval bound to the exact head and digest. It does not make the checks *mandatory*.

**The gap (reproduced, not inferred).** On `pull_request` the workflow files and the composite action `.github/actions/measurement-reference` come from the pull request itself. Proof PR #207 removes the reference step and the `check-tools` step from the `coverage` job: every check is green (13 passed, 2 skipped, 0 failed) and the job runs `go1.26.10` while the pin names `go1.26.11` (log in the cic-factory report `jobs/relay-ci-parity-06b-pin-protection/output/raw/207-coverage-job.txt`). Protecting the reference and enforcing the obligation to use it are two separate problems; PR #201 solves the first.

The same trust-boundary class, to be examined separately:
- the composite action (what it fetches, which ref and SHA it is given);
- the choice of the checking script (`GATE` / `MR_GATE`): the PR decides which script runs;
- the `BOOTSTRAP` mode: refused by the base script when the base already has the mechanism, but the mode is selected by the action;
- `scripts/object_model.py`: the pins come from the reference, the verifier itself runs from the pull request;
- the `baseline-guard` job has the same limit (the script runs from the base, its call lives in the PR's workflow).

**Acceptance criteria**
1. The enforcement works **outside the trust boundary of the pull request under verification**: a PR cannot remove, weaken or bypass a mandatory check by editing workflow files, the action, the gate selection or the bootstrap choice.
2. **#207 is the mandatory negative proof**: the same change that is green today must be rejected, with the reason in the log. Counter-probes show the protection is what changes the result.
3. The integrity of the action, the `GATE`/`MR_GATE` selection, `BOOTSTRAP` and `object_model.py` is examined one by one, each with its own negative proof or a documented residual gap.
4. A legitimate change of a workflow stays possible through a separate, owner-approved, visible path.
5. No new threshold, no toolchain change, no product code.

**Out of scope here:** which mechanism (required workflow, repository ruleset, a trigger that runs the base's workflow, or another one) is for the job spec and its review to decide; repository settings are an owner decision.

**Process (as decided in the #195 review):** first only a job-spec, implementation after its review. The implementation of PR-07 (FULL/DIFF integration) starts only after this issue is closed. The scheduled workflows (`mutation.yml`, `nightly.yml`) have no run in a pull request; their proof is an acceptance condition of PR-07.

