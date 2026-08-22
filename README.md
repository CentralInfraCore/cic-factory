# cic-factory-core

The reusable core of the CIC agent factory: job lifecycle, machine gates, and
agent-run tooling — extracted from
[`CentralInfraCore/cic-factory`](https://github.com/CentralInfraCore/cic-factory)
with history preserved.

The split follows one question per repo:

| repo | question it answers |
|---|---|
| `cic-factory-core` | what can the factory do in general? |
| `cic-factory` | how does CIC use it? |

## Status: round-one extraction, not yet a product

This repository holds the **CIC-coupled code as it stands today**, moved over
unchanged. Nothing was generalised, renamed, or restructured. The paths are the
ones the files had in `cic-factory`.

That is deliberate: the first split is history-preserving only, so that the
generalisation work that follows has a verifiable starting point rather than a
rewrite nobody can diff against.

**Do not depend on this repository yet.** There is no release, no contract, no
stability promise.

## What came over

The pre-SPEC defined the core as three things — tooling, the job schema, and
the lifecycle convention. All three are here.

**Implementation**

```
tools/run-job.sh                job lifecycle driver
tools/validate-spec.sh          pre-run machine gate (K1–K11)
tools/validate-output.sh        pre-merge machine gate (O1–O5)
tools/update-index.sh           job state map regeneration
tools/test-run-job-finalizer.sh finalizer test
tools/init-hooks.sh             git hook installation
tools/git_hook_commit-msg.sh    Vault commit signing hook
tools/install-claude-hooks.sh   agent hook installation
tools/cic-hooks.json            agent hook configuration
tools/hooks/                    context monitor, event log, no-ask-human guard
tools/env.sh.example            environment template
```

**Interface** — the operator's entry point to the lifecycle

```
.claude/commands/job-create.md    create a job spec
.claude/commands/job-validate.md  run the spec gate
.claude/commands/job-run.md       run a job
.claude/commands/job-review.md    review delegation
.claude/commands/job-close.md     close a job
.claude/commands/job-boot.md      orchestrator boot sequence
```

**Specification** — the lifecycle convention the tooling implements

```
SPEC.md                         roles, job lifecycle, the state machine,
                                the lease, "git is the source of trust",
                                the three machine gates
CLAUDE.md                       how to work on this repository
docs/onboarding.md              how the model is used in practice
jobs/.schema/meta.yaml          job spec schema — the single definition
.gitignore
```

`CLAUDE.md` arrived whole from `cic-factory` and has since been split: `SPEC.md`
carries the model, the CIC-specific half (ecosystem map, repo paths, MCP server,
reviewed threads) stayed behind in `cic-factory`, and what remains here is how to
develop this repository.

The schema is defined in exactly one place. It used to be restated in prose, and
the restatement fell three fields behind — `lease_expires`, `spec_gate`, `usage`.
The gate now refuses any document that redefines it.

`tools/relay-build-test.sh` was **not** extracted: it drives a CIC-Relay build
and is workflow, not core.

## Known coupling — what round two has to break

The extracted files still reference CIC-specific names. Measured across the
tracked set, excluding this README and `LICENSE.md`, which describe the
coupling rather than carry it:

| coupling | where |
|---|---|
| `cic-factory` repo name | `docs/onboarding.md`, 3 slash commands, `tools/hooks/context-monitor.sh`, `tools/env.sh.example`. **No longer in `tools/run-job.sh`** — the clone source is derived from the repository's own `origin`. |
| `kb_focus` (KB node ids) | `CLAUDE.md`, `docs/onboarding.md`, 2 slash commands, both gates, `tools/run-job.sh`, `jobs/.schema/meta.yaml` |
| `~/.claude-personal` agent layout | `CLAUDE.md`, `docs/onboarding.md`, `.claude/commands/job-run.md`, `tools/run-job.sh`, `tools/install-claude-hooks.sh`, `jobs/.schema/meta.yaml` |
| `CIC-Relay`, `$CIC_RELAY_PATH` | `CLAUDE.md`, `docs/onboarding.md`, `.claude/commands/job-boot.md`, both gates, `tools/env.sh.example`, `jobs/.schema/meta.yaml` |
| `cic-graph` MCP server | `CLAUDE.md`, `docs/onboarding.md`, 2 slash commands, `tools/run-job.sh` |
| `$CIC_MCP_*` | `CLAUDE.md`, `tools/run-job.sh`, `tools/env.sh.example` |
| `cic-my-sign-key` Vault key | `CLAUDE.md`, `tools/git_hook_commit-msg.sh` |
| `CIC-Schemas`, ProofTrace | `CLAUDE.md`, `tools/env.sh.example` |

Each of these is a place where the core currently knows something only CIC
should know.

## What the gate proves, and what it does not

`.github/workflows/gate.yml` checks that the shell, YAML, JSON and Python parse,
that shellcheck finds no error-severity defects, that `LICENSE` is unmodified,
and it runs two behavioural suites:

| suite | what it covers |
|---|---|
| `tools/test-run-job-finalizer.sh` | the finalizer trap: SIGPIPE, SIGTERM, closed stdout, and never leaving `meta.yaml` claiming `running` when nothing runs (15 checks) |
| `tools/test-lifecycle-transitions.sh` | the state transition `run-job.sh` performs, and the invariant that it can never write `done` (6 checks) |
| `tools/test-close-job.sh` | every refusal in `close-job.sh` — wrong status, failing output gate, missing/empty/unfinished review, an unacknowledged spec-gate bypass, a bypass hidden behind a YAML comment, an unknown gate value, malformed and duplicate-keyed metas — each against a fixture that violates it (48 checks) |
| `tools/test-run-job-spec-gate.sh` | that `run-job.sh` refuses a NO-GO spec, that `--skip-spec-gate` still starts, and that the bypass is recorded in `meta.yaml` (15 checks) |
| `tools/test-install-claude-hooks.sh` | that the hook installer converges — running it five times leaves the same file — and does not touch hooks it does not own (10 checks) |
| `tools/test-stale-jobs.sh` | that a job stuck in `running` past its lease is detected, against fixtures that are stuck on purpose, including a status hidden behind a trailing comment (18 checks) |
| `tools/test-check-docs.sh` | that the docs checker itself can fail — broken links, schema duplication, and files not yet added to git — against fixtures that violate each (12 checks) |
| `tools/test-run-job-e2e.sh` | **a whole job, `pending` → `awaiting_review` → `done`**, driven by the `echo` runner — no agent, no network, no cost (17 checks) |
| `tools/test-validate-meta.sh` | that the meta schema rejects what it should — a typo'd field name, an invalid `status`, an empty model, a missing block, a bad `job_id`, a schema that is itself malformed (17 checks) |
| `tools/test-verify-signatures.sh` | that the signature verifier can fail — tampered tree, missing metadata, forged signature, a merge smuggling content, a tag on a merge commit, an empty range (18 checks) |
| `tools/test-check-embedded-python.sh` | that the embedded-Python checker can fail — the `core/@v0.1.1` indentation error put back, an error behind a backslash-continued command, and a Python heredoc hidden behind a non-`PY` delimiter (15 checks) |
| `tools/test-context-monitor.sh` | that the context-monitor hook cannot be made to execute a command — a counter, an evacuation timestamp and a debug log line each carrying a command substitution, plus a symlinked state file and a state directory that is private and not in `/tmp` (18 checks) |
| `tools/test-meta-get.sh` | that one document reads the same whichever way it is written — quoted, bare, single-quoted, with a trailing comment — and that a duplicate key, malformed YAML or a non-scalar field fails closed rather than looking absent (19 checks) |
| `tools/test-commit-msg-signer.sh` | that the signer refuses rather than downgrading — no CA, a non-https endpoint, no token, an unreachable Vault — and that the token reaches curl through a 0600 config file, never the process list (25 checks) |

Every step was measured against a deliberately broken copy before it landed,
because a gate that cannot go red is decoration. That measurement is not a
formality: the finalizer suite passed 15/15 against a `run-job.sh` sabotaged to
close jobs as `done`, because it only extracts the prelude and the status
decision lives below it. The lifecycle suite exists to cover that blind spot.

There **is** now a test that runs a whole job — `test-run-job-e2e.sh`, made
possible by the `echo` runner. It found a defect on its first run that every
other gate had missed: a Python indentation error in `run-job.sh`'"'"'s
finalisation block, shipped in `core/@v0.1.1`, which crashed every job at the
moment it should have reached `awaiting_review`. Eight suites checking decisions
in isolation could not see it; one test that ran a job saw it immediately.

What the gate still does not prove: that a *real* agent run works. The echo
runner exercises the lifecycle, not Claude.

## Signatures are verified, not just written

The `commit-msg` hook signs every commit against a deterministic digest of its
tree. Until `tools/verify-signatures.sh` existed, **nothing read those signatures
back** — they were a claim, not evidence.

The gate now verifies every commit a PR introduces: the recorded digest must
equal a fresh digest of the tree, and the ECDSA signature must verify against the
certificate embedded in the same message. Verification is offline; the
certificate travels with the commit, and the signing token could not verify
anyway — its policy grants `transit/sign` but not `transit/verify`.

Merge commits are made server-side by GitHub, where no hook runs, so they cannot
be signed. They are held to a different rule instead: **a merge must introduce
nothing** — its tree has to equal one of its parents'. That preserves the actual
invariant, that every byte is covered by some signed commit, without pretending
the merge itself is signed. A merge that does introduce content must be signed
like anything else.

A release tag must point at a signed commit, never at a merge commit.

## A note on the commit signatures

Commits in `cic-factory` carry a Vault signature over the **full repository
tree**. A path-filtered history does not reproduce that tree, so those
signatures no longer verify here — 33 of the 43 extracted commits were
affected.

They were removed rather than carried over, because a signature that cannot
verify is worse than no signature: it reads as provenance. Each affected commit
message instead names its original signed commit in `cic-factory`, where the
signature still holds.

Commits made in this repository are signed normally and verify against their
own tree.

## Licence

**AGPL-3.0-or-later**, with an attribution term under section 7(b) — the common
core stays open, including for network use, while products built against its
contract boundary stay free. See [`LICENSE.md`](LICENSE.md) for why this differs
from the CC BY-NC-SA 4.0 licence most CIC repositories inherit.
