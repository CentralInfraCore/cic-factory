# Makefile for cic-object-model — the normative CIC object model spec,
# its conformance vectors, and the Go + Rust reference implementations.
#
# mk/rust.mk is NOT present yet: the Rust gate is extracted from
# CIC-Relay/Makefile by the cic-object-model-rust sub-job. See
# docs/rust-gate-extraction.md for the line-referenced recipe. Until that
# job lands, `make rust` is unavailable and CI runs the Go gate only.

# ---- Includes ----
include mk/infra.mk
include mk/golang.mk
-include mk/rust.mk

# ---- Phony ----
.PHONY: all help validate release test up down shell build fmt lint check typecheck repo.init manifest-verify manifest-update docs.link-check conformance

# Default to showing help
all: help

# =============================================================================
# Compiler Flags (can be overridden on command line, e.g., make release VERBOSE=1)
# =============================================================================
VERBOSE ?=
DEBUG ?=
DRY_RUN ?=
VERSION ?= # New: Version for release command
GIT_TIMEOUT ?= 60
VAULT_TIMEOUT ?= 10
TEST_FILE ?= # New: Specify a specific test file (e.g., tests/test_compiler.py)
TEST_NAME ?= # New: Specify a specific test function name (e.g., test_load_yaml_valid)

# Construct COMPILER_CLI_ARGS based on VERBOSE and DEBUG flags
COMPILER_CLI_ARGS =
ifeq ($(VERBOSE),1)
    COMPILER_CLI_ARGS += --verbose
endif
ifeq ($(DEBUG),1)
    COMPILER_CLI_ARGS += --debug
endif
ifeq ($(DRY_RUN),1)
    COMPILER_CLI_ARGS += --dry-run
endif
COMPILER_CLI_ARGS += --git-timeout $(GIT_TIMEOUT)
COMPILER_CLI_ARGS += --vault-timeout $(VAULT_TIMEOUT)

# Construct PYTEST_ARGS based on TEST_FILE and TEST_NAME
PYTEST_ARGS =
ifeq ($(TEST_FILE),)
    PYTEST_ARGS += tests/
else
    PYTEST_ARGS += $(TEST_FILE)
endif
ifeq ($(TEST_NAME),)
    # No specific test name
else
    PYTEST_ARGS += -k "$(TEST_NAME)"
endif


# =============================================================================
# Container Lifecycle Management (Aliases)
# =============================================================================

up: infra.up
down: infra.down
shell: infra.shell
build: infra.build

# =============================================================================
# Main Development Tasks
# =============================================================================

validate:
	@echo "--- Validating all schemas against the meta-schema ---"
	@docker compose exec builder python -m tools.compiler validate $(COMPILER_CLI_ARGS)

release:
ifeq ($(VERSION),)
	$(error VERSION is required for the release command. Usage: make release VERSION=1.0.0)
endif
	@echo "--- Building and signing release schemas ---"
	# Pass Git author and committer identity from host to container for commit operations
	@docker compose exec \
		-e GIT_AUTHOR_NAME="$(shell git config user.name)" \
		-e GIT_AUTHOR_EMAIL="$(shell git config user.email)" \
		-e GIT_COMMITTER_NAME="$(shell git config user.name)" \
		-e GIT_COMMITTER_EMAIL="$(shell git config user.email)" \
		builder python -m tools.compiler release --version $(VERSION) $(COMPILER_CLI_ARGS)
	# The release.sh script is no longer needed as its functionality has been integrated into compiler.py
	# @tools/release.sh project.yaml
	# @git add project.yaml # This is now handled by compiler.py

test: infra.test

# =============================================================================
# Manifest Management
# =============================================================================

manifest-verify: ##manifest-verify
	@echo "--- Verifying repository manifest ---"
	@docker compose exec builder sh -c 'test -f MANIFEST.sha256 && sha256sum -c MANIFEST.sha256'

manifest-update: ##manifest-update
	@echo "--- Updating repository manifest ---"
	@docker compose exec builder sh -c 'git ls-files -z \
		| xargs -0 sha256sum' | grep -v "MANIFEST.sha256" | LC_ALL=C sort > MANIFEST.sha256
	@echo "MANIFEST.sha256 updated"

# =============================================================================
# Documentation
# =============================================================================

docs.link-check: ## Verify internal markdown links in docs/ and READMEs resolve
	@echo "--- Checking internal documentation links ---"
	@docker compose exec -T builder python tools/check_doc_links.py

# =============================================================================
# Conformance
# =============================================================================

# The conformance vectors are the falsifiable part of SPEC.md. They are
# implementation-independent (YAML in, YAML out), so every implementation
# runs the same corpus. This target dispatches to whichever implementations
# are present; with neither go/ nor rust/ populated it reports that fact
# rather than passing vacuously.
conformance: ## Run the conformance corpus against every present implementation
	@echo "--- Running conformance vectors ---"
	@ran=0; \
	if [ -f go/go.mod ]; then $(MAKE) golang.test && ran=1; fi; \
	if [ -f rust/Cargo.toml ] && [ -f mk/rust.mk ]; then $(MAKE) test-rust && ran=1; fi; \
	if [ "$$ran" -eq 0 ]; then \
		echo "NO IMPLEMENTATION PRESENT — 0 vectors executed."; \
		echo "The vector corpus exists but is unverified until go/ or rust/ lands."; \
		exit 1; \
	fi

# =============================================================================
# Code Quality & Formatting (Aliases)
# =============================================================================

fmt: infra.fmt
lint: infra.lint
typecheck: infra.typecheck
check: infra.check

# =============================================================================
# Repository Setup (Aliases)
# =============================================================================

repo.init: infra.repo.init

# =============================================================================
# Help
# =============================================================================

help:
	@echo "Usage: make [target] [OPTIONS]"
	@echo ""
	@echo "--- High-Level Project Commands ---"
	@echo "Development Environment:"
	@echo "  up            Start the development environment."
	@echo "  down          Stop and remove the development environment."
	@echo "  shell         Open an interactive shell into the running environment."
	@echo "  build         Build the development environment."
	@echo ""
	@echo "Main Tasks:"
	@echo "  validate      Run fast, offline validation of all schemas."
	@echo "  release       Build, checksum, and sign all non-dev schemas (requires Vault)."
	@echo "  test          Run pytest for the compiler infrastructure code."
	@echo ""
	@echo "Manifest Management:"
	@echo "  manifest-verify  Verify the integrity of the repository using MANIFEST.sha256."
	@echo "  manifest-update  Re-generate the MANIFEST.sha256 file."
	@echo ""
	@echo "Documentation:"
	@echo "  docs.link-check  Verify internal markdown links in docs/ and READMEs resolve."
	@echo ""
	@echo "Options for validate/release:"
	@echo "  VERBOSE=1     Enable verbose output."
	@echo "  DEBUG=1       Enable debug output (most verbose)."
	@echo "  DRY_RUN=1     Perform a trial run without making any changes."
	@echo "  VERSION=X.Y.Z The semantic version to release (e.g., 1.0.0). Required for 'release' command."
	@echo "  GIT_TIMEOUT=N Set Git command timeout in seconds (default: 60)."
	@echo "  VAULT_TIMEOUT=N Set Vault API call timeout in seconds (default: 10)."
	@echo ""
	@echo "Options for test:"
	@echo "  TEST_FILE=path/to/file.py  Specify a single test file to run."
	@echo "  TEST_NAME=test_function    Specify a single test function to run (can be combined with TEST_FILE)."
	@echo ""
	@echo "Code Quality & Formatting:"
	@echo "  fmt           Format all code."
	@echo "  lint          Lint all code and files."
	@echo "  typecheck     Run static type checking."
	@echo "  check         Run all code quality checks (fmt, lint, typecheck)."
	@echo ""
	@echo "Repository Setup:"
	@echo "  repo.init     Set up the Git hooks for this repository."
	@echo ""
	@echo "Maintenance:"
	@echo "  infra.deps    (Re)generate and install dependencies."
	@echo "  infra.coverage Generate code coverage report."
	@echo "  infra.clean   Remove all generated files and caches."
	@$(MAKE) infra.help
