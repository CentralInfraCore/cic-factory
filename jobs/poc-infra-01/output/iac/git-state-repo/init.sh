#!/usr/bin/env bash
set -euo pipefail

# Run on the Relay VM (or Bastion, if the Relay can reach it over the VCN).
# Initializes the bare git state repo and creates the orphan `state` and
# `intent` branches consumed by GitStateRecorder (system-plan.md 1.4).

REPO_DIR="${REPO_DIR:-/srv/cic-state.git}"
WORK_DIR="$(mktemp -d)"

mkdir -p "${REPO_DIR}"
git init --bare "${REPO_DIR}"

git clone "${REPO_DIR}" "${WORK_DIR}/work"
cd "${WORK_DIR}/work"

git checkout --orphan state
git commit --allow-empty -m "init: state branch"

git checkout --orphan intent
git commit --allow-empty -m "init: intent branch"

git push origin state intent

cd /
rm -rf "${WORK_DIR}"

echo "Bare git state repo ready at ${REPO_DIR} (branches: state, intent)"
