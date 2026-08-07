#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PYTHON_CMD="python3 tools/compiler.py"
SOURCES_DIR="sources"
DEPENDENCIES_DIR="dependencies"
RELEASES_DIR="release"
CANONICAL_SOURCE_FILE="schemas/index.yaml"
VAULT_TOKEN_FILE="/var/run/secrets/vault-token"

# --- Load Vault Token from mounted secret ---
if [ ! -f "$VAULT_TOKEN_FILE" ]; then
    echo "[ERROR] Vault token file not found at $VAULT_TOKEN_FILE"
    exit 1
fi
export VAULT_TOKEN=$(cat "$VAULT_TOKEN_FILE")

# --- Input Validation ---
RELEASE_TYPE=$1
VERSION=$2

if [ -z "$RELEASE_TYPE" ] || [ -z "$VERSION" ]; then
    echo "[ERROR] Usage: $0 [dependency|schema] <version>"
    echo "Example: $0 dependency v1.0.0"
    exit 1
fi

if [[ "$VERSION" == *".dev"* ]]; then
    echo "[ERROR] Release version cannot be a '.dev' version."
    exit 1
fi

# --- Pre-flight Checks ---
echo "--- Checking Git working directory status ---"
if [ -n "$(git status --porcelain)" ]; then
    echo "[ERROR] Git working directory is not clean. Please commit or stash your changes before releasing."
    exit 1
fi
echo "  ✓ Git working directory is clean"

echo "--- Running pre-release validation ---"
$PYTHON_CMD validate
echo "  ✓ Pre-release validation passed"

# --- Get Schema Name ---
echo "--- Getting schema name from source ---"
SCHEMA_NAME=$($PYTHON_CMD get-name)
if [ -z "$SCHEMA_NAME" ]; then
    echo "[ERROR] Could not determine schema name from '$CANONICAL_SOURCE_FILE'."
    exit 1
fi
echo "  - Schema name: $SCHEMA_NAME"

# --- Git Operations ---
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
RELEASE_BRANCH="${SCHEMA_NAME}/releases/${VERSION}"
TAG_NAME="${SCHEMA_NAME}@${VERSION}"

echo "--- Starting Release Process for ${TAG_NAME} ---"
echo "[INFO] Current branch: $CURRENT_BRANCH"
echo "[INFO] Creating release branch: $RELEASE_BRANCH"
git checkout -b "$RELEASE_BRANCH"

# --- Artifact Generation ---
echo "[INFO] Generating signed artifact..."
if [ "$RELEASE_TYPE" == "dependency" ]; then
    $PYTHON_CMD release-dependency --source "$CANONICAL_SOURCE_FILE" --version "$VERSION"
    OUTPUT_FILE="${DEPENDENCIES_DIR}/${SCHEMA_NAME}-${VERSION}.yaml"
elif [ "$RELEASE_TYPE" == "schema" ]; then
    $PYTHON_CMD release-schema --source "$CANONICAL_SOURCE_FILE" --version "$VERSION"
    OUTPUT_FILE="${RELEASES_DIR}/${SCHEMA_NAME}-${VERSION}.yaml"
else
    echo "[ERROR] Invalid release type '$RELEASE_TYPE'. Must be 'dependency' or 'schema'."
    git checkout "$CURRENT_BRANCH"
    git branch -D "$RELEASE_BRANCH"
    exit 1
fi

# --- Final Git Operations ---
echo "[INFO] Adding generated file to Git: $OUTPUT_FILE"
git add "$OUTPUT_FILE"

echo "[INFO] Committing release (skipping commit-msg hook)..."
git commit --no-verify -m "Release ${TAG_NAME}"

echo "[INFO] Creating annotated tag: ${TAG_NAME}"
git tag -a "$TAG_NAME" -m "Release ${TAG_NAME}"

echo "[INFO] Switching back to original branch: $CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH"

echo "[INFO] Deleting local release branch: $RELEASE_BRANCH"
git branch -D "$RELEASE_BRANCH"

# --- Success Message ---
echo ""
echo "✓ Successfully created release tag '${TAG_NAME}'."
echo "  To publish, run:"
echo "  git push origin ${TAG_NAME}"
