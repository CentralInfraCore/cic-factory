# ---- Go quality gate for go/ (the reference implementation) ----
#
# Inherited from base-repo wasm/main (which inherited it from CIC-Relay) and
# retargeted from module/ to go/ via GO_MODULE_DIR — a one-line change, which
# is why this branch was chosen over golang/main (see docs/branch-decision.md).
#
# It provides `golang.quality` (fmt-check/vet/lint/vuln) and `golang.test`,
# used by the CI Go gate and by `make check`'s sibling targets. The
# relay-specific build/release/canonicalize/crt_parser/mq-publish machinery
# was already removed upstream — it referenced packages and services that do
# not exist here.
#
# mk/rust.mk is its intended sibling: same container-exec shape, RUST_EXEC in
# place of GO_EXEC. It is extracted from CIC-Relay/Makefile by the
# cic-object-model-rust sub-job (docs/rust-gate-extraction.md).

.PHONY: golang.all golang.help golang.fmt golang.fmt-check golang.lint golang.vet golang.quality \
	golang.test golang.coverage golang.coverage-profile golang.coverage-html golang.coverage-threshold \
	golang.vuln golang.deps golang.clean golang.tdd

# Default to showing help
golang.all: golang.help

VERSION  ?= dev
COMMIT   ?= $(shell git rev-parse --short HEAD)
BUILD_DIR ?= ./output/$(COMMIT)

# ---- Coverage outputs ----
COVERAGE_FILE ?= /output/$(COMMIT)/coverage.out
COVERAGE_HTML ?= /output/$(COMMIT)/coverage.html

GOFLAGS  ?= -mod=readonly -trimpath

# Kapcsolható race detektor: dev/CI ON, release OFF (RACE=0)
RACE ?= 1
ifeq ($(RACE),1)
  GO_RACE := -race
else
  GO_RACE :=
endif

# GO_MODULE_DIR: where the Go module lives relative to /app. This repo's
# reference implementation is at go/ (go/go.mod), populated by the
# cic-object-model-go sub-job.
GO_MODULE_DIR ?= go

define GO_EXEC
	docker compose exec -T builder sh -eu -o pipefail -c 'cd /app/$(GO_MODULE_DIR) && $(1)'
endef
define GO_FIXER
	docker compose exec -T builder sh -eu -o pipefail -c 'cd /app/$(GO_MODULE_DIR) && $(1)'
endef

# Clean output for this commit
golang.clean:
	rm -rf $(BUILD_DIR)
	@echo "Cleaned build output for commit $(COMMIT)"

# ---- Help ----
golang.help: ## Show available make targets
	@echo "Available targets:"
	@grep -E '^golang\.[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---- Dependency Management ----
golang.deps: ## Tidy go module files
	@echo "Tidying go module files..."
	@$(call GO_FIXER, go mod tidy)

# ---- Quality gate ----
golang.fmt: ## Apply gofmt -s (and goimports if available)
	$(call GO_FIXER, git config --global --add safe.directory /app && \
		git ls-files -z -- "*.go" | xargs -0 gofmt -s -w ; \
		if command -v goimports >/dev/null 2>&1; then \
			git ls-files -z -- "*.go" | xargs -0 goimports -w ; \
		fi )

golang.fmt-check: ## Fail if formatting differs
	$(call GO_EXEC, M="$$(git ls-files -z -- "*.go" | xargs -0 gofmt -s -l)"; \
		test -z "$$M" || { printf "%s\n" "$$M"; echo "Code not formatted. Run make golang.fmt"; exit 1; })

golang.lint: ## Run static linters (staticcheck, ineffassign)
	mkdir -p $(BUILD_DIR) && $(call GO_EXEC, \
		set -euo pipefail; \
		PKGS="$$(go list ./... | grep -v /vendor/)"; \
		if [ -z "$$PKGS" ]; then \
			echo "No Go packages to lint."; \
			exit 0; \
		fi; \
		echo "Staticcheck on: $$PKGS"; \
		GO111MODULE=on GOFLAGS="$(GOFLAGS)" staticcheck $$PKGS \
	)

golang.vet: ## Run go vet
	mkdir -p $(BUILD_DIR) && $(call GO_EXEC, \
		set -euo pipefail; \
		PKGS="$$(go list ./... | grep -v /vendor/)"; \
		if [ -z "$$PKGS" ]; then \
			echo "No Go packages to lint."; \
			exit 0; \
		fi; \
		echo "Vet on: $$PKGS"; \
		GO111MODULE=on GOFLAGS="$(GOFLAGS)" go vet $$PKGS \
	)

golang.vuln: ## Run Go vulnerability scan (govulncheck)
	mkdir -p $(BUILD_DIR) && $(call GO_EXEC, \
		set -euo pipefail; \
		PKGS="$$(go list ./... | grep -v /vendor/)"; \
		if [ -z "$$PKGS" ]; then \
			echo "No Go packages to lint."; \
			exit 0; \
		fi; \
		echo "govulncheck on: $$PKGS"; \
		GO111MODULE=on GOFLAGS="$(GOFLAGS)" govulncheck $$PKGS \
	)

golang.quality: golang.fmt-check golang.lint golang.vet golang.vuln ## Quality gate: all checks must pass

# ---- Tests & coverage ----
golang.test: ## Run unit tests (verbose, race)
	mkdir -p $(BUILD_DIR) && $(call GO_EXEC, \
		set -euo pipefail; \
		PKGS="$$(go list ./... | grep -v /vendor/)"; \
		if [ -z "$$PKGS" ]; then \
			echo "No Go packages to test."; \
			exit 0; \
		fi; \
		echo "Test on: $$PKGS"; \
		GO111MODULE=on GOFLAGS="$(GOFLAGS)" go test $(GO_RACE) -v $$PKGS \
	)

golang.coverage: golang.coverage-profile golang.coverage-html ## Run tests with coverage (profile + HTML)
	@echo "Coverage HTML: $(COVERAGE_HTML)"

golang.coverage-profile: ## Run tests with coverage (profile)
	mkdir -p $(BUILD_DIR) && $(call GO_EXEC, \
		set -euo pipefail; \
		PKGS="$$(go list ./... | grep -v /vendor/)"; \
		if [ -z "$$PKGS" ]; then \
			echo "No Go packages to test."; \
			exit 0; \
		fi; \
		GOFLAGS="$(GOFLAGS)" go test $(GO_RACE) -covermode=atomic -coverprofile=$(COVERAGE_FILE) $$PKGS \
	)

golang.coverage-html: ## Run tests with coverage (HTML)
	$(call GO_EXEC, mkdir -p $(BUILD_DIR) \
		&& go tool cover -html=$(COVERAGE_FILE) -o $(COVERAGE_HTML))

COVERAGE_MIN ?= 85

golang.coverage-threshold: golang.coverage ## Fail if coverage < $(COVERAGE_MIN)%
	mkdir -p $(BUILD_DIR) && docker compose exec -T builder sh -c 'cd /app/$(GO_MODULE_DIR) && \
		go tool cover -func=$(COVERAGE_FILE) | \
		awk -v MIN=$(COVERAGE_MIN) '"'"'/^total:/ { gsub("%","",$$3); v=$$3+0 } END { if (v < MIN) { printf "Coverage below %d%% (got %.1f%%)\n", MIN, v; exit 1 } else { printf "Coverage OK: %.1f%% >= %d%%\n", v, MIN } }'"'"''

# ---- Optional: TDD loop ----
golang.tdd: ## TDD loop with reflex
	$(call GO_EXEC, \
		command -v reflex >/dev/null 2>&1 || go install github.com/cespare/reflex@latest; \
		reflex -r "(\.go|go\.mod|go\.sum)$$" -- sh -c "GOFLAGS=-mod=readonly\ -trimpath go test -race -count=1 ./..." \
	)
