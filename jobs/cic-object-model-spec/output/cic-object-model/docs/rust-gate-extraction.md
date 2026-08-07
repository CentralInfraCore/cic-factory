# `mk/rust.mk` — extraction recipe

`mk/rust.mk` does not exist in this repository, and it does not exist anywhere
else either: `base-repo` has no `rust/*` branch, and no `mk/rust.mk` exists in
any CIC repository. The only Rust build and quality machinery in the ecosystem
lives **inline** in one file:

```
/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Relay/Makefile
```

This document is the line-referenced recipe for lifting it out. It is written
for the `cic-object-model-rust` sub-job, which owns the extraction.

**Verified 2026-08-07** by reading the source file, not by grep inference. Line
numbers are as of that reading; re-verify before relying on them.

---

## What to lift

### 1. The pinned toolchain — `docker-compose.yml`, not the Makefile

The image pin is **not** in the Makefile. `RUST_IMAGE_DIGEST` derives it from a
YAML anchor so that it cannot drift:

```make
# CIC-Relay/Makefile:44-46
# RUST_IMAGE_DIGEST: same single-source discipline for the rust-builder image —
# derived from the &rust_image anchor in docker-compose.yml so it cannot drift.
RUST_IMAGE_DIGEST ?= $(shell grep '^x-rust-version:' docker-compose.yml | grep -oE 'sha256:[a-f0-9]{64}')
```

The pin itself:

```yaml
# CIC-Relay/docker-compose.yml:15
x-rust-version: &rust_image rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8
```

**Both must be lifted together.** Taking the Makefile line alone yields a
`RUST_IMAGE_DIGEST` that silently evaluates to empty — a `$(shell grep ...)`
against a file with no such anchor produces no error, just an empty string.
That is a quiet failure of exactly the class this ecosystem is built to
prevent.

### 2. The `rust-builder` service

```yaml
# CIC-Relay/docker-compose.yml:119-136
rust-builder:
  image: *rust_image
  container_name: cic-rust-builder
  volumes:
    - ./:/git-source:ro
    - ~/tmp/cache/CIC-Relay/rust-cargo:/cargo
    - ~/tmp/cache/CIC-Relay/rust-target:/target
    - ./output:/output
  environment:
    - CARGO_HOME=/cargo
    - CARGO_TARGET_DIR=/target
    - CARGO_TERM_COLOR=never
  working_dir: /git-source
  stdin_open: true
  tty: true
  entrypoint: ["sh"]
```

Adaptations for this repository: rename the container
(`cic-object-model-rust-builder`), repoint the cache volumes, and **drop the
`./output:/output` mount** — it exists so the Go cgo build can link the
`cic-ffi` staticlib, which has no counterpart here.

### 3. `RUST_EXEC`

```make
# CIC-Relay/Makefile:114-118
# RUST_EXEC: run a cargo command in the rust-builder. Ensures rustfmt/clippy are
# present (idempotent, cheap once installed) so every rust target is self-sufficient.
define RUST_EXEC
	docker compose exec -T rust-builder bash -eu -o pipefail -c 'cd /git-source && rustup component add rustfmt clippy >/dev/null 2>&1 || true; $(1)'
endef
```

This is the sibling of `mk/golang.mk`'s `GO_EXEC` — same shape, same
discipline. Keeping them symmetrical is the reason `wasm/main` was chosen as
this repository's base (see [`branch-decision.md`](branch-decision.md)).

### 4. The gate targets — `Makefile:310-351`

Lift verbatim, renaming to the `rust.` namespace to match `mk/golang.mk`'s
`golang.` prefix:

| CIC-Relay target | Line | Becomes | Command |
|---|---|---|---|
| `fmt-rust` | 312 | `rust.fmt` | `cargo fmt --all` |
| `fmt-rust-check` | 316 | `rust.fmt-check` | `cargo fmt --all --check` |
| `lint-rust` | 319 | `rust.lint` | `cargo clippy --all-targets --all-features --locked -- -D warnings` |
| `test-rust` | 323 | `rust.test` | `cargo test --all --locked` |
| `coverage-rust` | 330 | `rust.coverage` | `cargo llvm-cov --all --locked --fail-under-lines $(RUST_COV_MIN)` |
| `deny-rust` | 337 | `rust.deny` | `cargo deny check` |
| `release-rust` | 343 | `rust.release` | `cargo build --release --locked --workspace` |
| `rust` | 351 | `rust.quality` | `rust.fmt-check rust.lint rust.coverage rust.deny` |

The coverage floor:

```make
# CIC-Relay/Makefile:328-329
# Line-coverage floor, to ratchet up (never down) — parity with the Go per-package
# thresholds and the Python --cov-fail-under gate.
RUST_COV_MIN ?= 90
```

`cargo-llvm-cov` and `cargo-deny` are installed on demand inside the target
(`Makefile:332-335`, `339-341`) rather than baked into the image.

`release-rust` (`:343-349`) sets
`RUSTFLAGS="--remap-path-prefix=/git-source=."` for reproducible paths. Worth
keeping — reproducibility is the point of the release story.

---

## What NOT to lift

`Makefile:362, 396, 420, 549` build `cic-ffi` and copy `libcic_ffi.a` into
`$(FFI_LIB_DIR)` for the Go cgo link. That is the relay's FFI boundary
(`features/feature-008/ffi-boundary.md`). This repository's Go and Rust
implementations are **independent implementations of the same specification**,
not two halves of one binary — they must not link to each other. Lifting the
FFI machinery would couple them and destroy the whole point of having two: that
they check each other by agreeing on the vector corpus.

---

## Wiring into this repository

1. Add `x-rust-version` anchor + `rust-builder` service to `docker-compose.yml`.
2. Create `mk/rust.mk` with `RUST_IMAGE_DIGEST`, `RUST_EXEC`, `RUST_COV_MIN`
   and the eight `rust.*` targets.
3. The root `Makefile` already carries `-include mk/rust.mk` (optional include,
   so the absence of the file is not an error today). Add the aliases
   `rust: rust.quality` and extend `check`.
4. `.github/workflows/ci.yml` already has a `Rust quality gate (rust/)` step
   guarded on `hashFiles('rust/Cargo.toml')`. It activates when `rust/` is
   populated; no CI edit is needed.

## Verification required from the sub-job

Not "the file exists", and not "`make rust.quality` exits 0" — an exit code
from a target whose container never started is not a passing gate.

- `docker compose config` resolves the `*rust_image` anchor to the pinned
  digest — paste it;
- `make rust.lint` output showing clippy actually ran over the crate;
- `make rust.coverage` output showing the measured percentage against
  `RUST_COV_MIN`;
- the conformance run: number of vectors executed, passed, failed.
