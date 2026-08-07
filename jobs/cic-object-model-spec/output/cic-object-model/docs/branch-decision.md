# Why this repository was bootstrapped from `base-repo` `wasm/main`

Measured on 2026-08-07 against `git@github.com:CentralInfraCore/base-repo.git`.

## The branch list is larger than expected

The two candidates put forward were `golang/main` and `wasm/main`, with the
note that `golang/devel` and `wasm/main` exist and no `rust/*` does.

`git branch -r` reports **32 remote branches**. The absence of `rust/*` is
confirmed — there is no Rust template anywhere in `base-repo`. But four
template lines that were not mentioned do exist, and one of them is a direct
contender that had to be evaluated:

| Branch | Files | Last commit | Note |
|---|---|---|---|
| `golang/main` | 39 | 2025-10-01 | candidate |
| `golang/devel` | 59 | 2025-12-13 | |
| `wasm/main` | 100 | **2026-06-14** | candidate — freshest |
| `schemas/main` | 82 | 2026-03-21 | **not mentioned; a schema-repo template** |
| `main` | 87 | 2026-03-25 | |
| `docs/main` | 18 | 2025-10-01 | docs only |
| `workflows/main` | 19 | 2025-10-02 | |

`schemas/main` deserved evaluation on its face: this repository *is* a schema
repository, and that branch ships `schemas/index.yaml`, `go.meta.schema.yaml`
and `source/` — purpose-built for exactly this shape of project.

## The deciding criterion

Not size. The question is which branch reaches "Go **and** Rust quality gates
run, manifest integrity is enforced, commits are Vault-signed" with the least
work.

| Requirement | `golang/main` | `schemas/main` | `wasm/main` |
|---|---|---|---|
| Modular `mk/` | ✗ (monolithic Makefile) | partial (`infra.mk` only) | ✓ `infra.mk`, `golang.mk`, `wasm.mk` |
| Go quality gate | ✓ but inline, not modular | **✗ absent** | ✓ `mk/golang.mk` |
| Retargetable to `go/` | rewrite | build from scratch | ✓ one line |
| `MANIFEST.sha256` + `manifest-verify` | ✓ | ✓ | ✓ |
| `docs.link-check` | ✗ | ✗ | ✓ |
| CI workflow | 2 workflows, older | ✓ | ✓ |
| `project.yaml` Vault chain | ✗ | ✓ | ✓ |
| Freshness | 2025-10 | 2026-03 | **2026-06** |

`schemas/main` loses on the one thing that mattered most: it has **no Go gate
at all** (`mk/infra.mk` only). Its schema-repo affordances are files, which are
cheap to add; a quality gate is machinery, which is not.

`golang/main` has a thorough Go gate, but inline in a 300-line monolithic
Makefile with no `mk/` directory. Adding a Rust gate beside it means either
restructuring into `mk/` first or bolting Rust onto the monolith. It also
predates the infra migration by eight months.

## The decisive detail

`wasm/main`'s `mk/golang.mk` is already parameterized:

```make
GO_MODULE_DIR ?= module
```

Retargeting the entire Go gate at this repository's `go/` directory is that one
line. And the file's shape — a `GO_EXEC` macro running commands in a pinned
builder container — is the same shape `CIC-Relay`'s `RUST_EXEC` uses, so
`mk/rust.mk` drops in beside it as a sibling with no structural adaptation.
That is the whole argument: `wasm/main` is the only branch where both gates end
up looking like each other.

## Direction of travel: subtract, don't add

The removal from `wasm/main` is bounded and enumerable — WASM coupling in the
Makefile is one `include` line plus one target:

| Removed | Was |
|---|---|
| `module/` | the WASM guest module (13 files) |
| `abi.schema.yaml` | guest↔host ABI schema |
| `mk/wasm.mk` | TinyGo build/rebuild-verify targets |
| `docs/contracts/**` | envelope / host-expectations / release-artifact / wasm-abi |
| `docs/{en,hu}/wasm-module-authoring.md` | guest authoring guide |
| `tools/verify_release.py` | checks `module.wasm` against `buildHash` |
| `Makefile: include mk/wasm.mk`, `verify-release` | the only two WASM references |
| `Dockerfile`: TinyGo + `wabt` | no guest is compiled here |
| `project.yaml`: `abi:` block | described exported WASM symbols |
| `project.schema.yaml`: `abi` required + `$ref` | followed the block |
| `features/`, `feature-list.md`, `README.hu.md` | template boilerplate |

Adding the same machinery to `golang/main` would have meant writing `mk/`,
`docs.link-check`, `project.yaml`'s Vault chain, and the CI workflow — building,
not deleting. Deleting a known list is verifiable; building machinery is not,
especially without the ability to run it.

## What was verified and what was not

**Verified:** branch inventory, file counts, last-commit dates, Makefile target
lists, the `GO_MODULE_DIR` parameterization, the exhaustive WASM reference
list (by grep after each removal), and that no internal documentation link is
left dangling except in `README.md`, which was rewritten.

**Not verified:** that `make build`, `make check` or CI actually succeed. All of
those require Docker, which was not available in the environment where this
repository was assembled. The skeleton is structurally consistent and
unexecuted — see `../README.md` and the job's claim-evidence table.
