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

This repository currently holds the **CIC-coupled code as it stands today**,
moved over unchanged. Nothing was generalised, renamed, or restructured. The
paths are the ones the files had in `cic-factory`.

That is deliberate: the first split is history-preserving only, so that the
generalisation work that follows has a verifiable starting point rather than a
rewrite nobody can diff against.

**Do not depend on this repository yet.** There is no release, no contract, no
stability promise.

## What came over

```
jobs/.schema/meta.yaml          job spec schema (required fields)
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

`tools/relay-build-test.sh` was **not** extracted: it drives a CIC-Relay build
and is workflow, not core.

## Known coupling — what round two has to break

The extracted scripts still reference CIC-specific names. Measured, not
estimated:

| coupling | where |
|---|---|
| `cic-graph` MCP server | `tools/run-job.sh` |
| `kb_focus` (KB node ids) | `tools/run-job.sh`, `tools/validate-spec.sh`, `jobs/.schema/meta.yaml` |
| `CIC-Relay`, `$CIC_RELAY_PATH` | `tools/env.sh.example`, `jobs/.schema/meta.yaml`, both gates |
| `$CIC_MCP_*` | `tools/run-job.sh`, `tools/env.sh.example` |
| `cic-factory` repo name | `tools/run-job.sh`, `tools/hooks/context-monitor.sh`, and others |
| `~/.claude-personal` agent layout | `tools/run-job.sh`, `tools/install-claude-hooks.sh` |
| `cic-my-sign-key` Vault key | `tools/git_hook_commit-msg.sh` |

Each of these is a place where the core currently knows something only CIC
should know.

## A note on the commit signatures

Commits in `cic-factory` carry a Vault signature over the **full repository
tree**. A path-filtered history does not reproduce that tree, so those
signatures no longer verify here — 24 of the 33 commits were affected.

They were removed rather than carried over, because a signature that cannot
verify is worse than no signature: it reads as provenance. Each affected commit
message instead names its original signed commit in `cic-factory`, where the
signature still holds.

## Licence

Intended: **AGPL-3.0-or-later**, with attribution — the common core stays open.
Not yet applied; no `LICENSE` file has been committed.
