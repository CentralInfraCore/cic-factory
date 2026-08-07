#!/usr/bin/env bash
set -euo pipefail

# Commit message fájl (Git adja paraméterként)
COMMIT_MSG_FILE="$1"

# --- Vault Configuration ---
# Use environment variables for paths if they exist, otherwise use local defaults.
# This allows the script to run both locally and inside a Docker container.
VAULT_TOKEN_FILE="${CIC_VAULT_TOKEN_FILE:-$XDG_RUNTIME_DIR/vault/sign-token}"
VAULT_CA_CERT_FILE="${CIC_VAULT_CA_FILE:-$XDG_RUNTIME_DIR/vault/server.crt}"
VAULT_ADDR="${VAULT_ADDR:-https://127.0.0.1:18200}" # Default to local dev server
KEY_NAME="cic-my-sign-key"

# --- Load Vault Token from file ---
if [ ! -f "$VAULT_TOKEN_FILE" ]; then
    echo "[!] Vault token file not found at $VAULT_TOKEN_FILE"
    exit 1
fi
export VAULT_TOKEN=$(cat "$VAULT_TOKEN_FILE")

# --- Helper for curl ---
CURL_OPTS=""
if [ -f "$VAULT_CA_CERT_FILE" ]; then
  CURL_OPTS="--cacert $VAULT_CA_CERT_FILE"
else
  echo "[WARNING] Vault CA certificate not found. Proceeding without TLS verification."
  CURL_OPTS="-k"
fi

# ===== Staged tartalom snapshot =====
if ! TREE_ID=$(git write-tree 2>/dev/null); then
  echo "[*] Nothing staged; skipping signing."
  exit 0
fi

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# Kibontjuk, majd determinisztikus tar streamet készítünk
git archive --format=tar "$TREE_ID" | tar -xf - -C "$tmpdir"
DIGEST_B64=$(tar --sort=name --mtime='UTC 1970-01-01' \
  --owner=0 --group=0 --numeric-owner -cf - -C "$tmpdir" . \
  | openssl dgst -sha256 -binary | openssl base64 -A)

# ===== Vault aláírás =====
SIGNATURE_RESPONSE=$(curl -s ${CURL_OPTS} \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -X POST \
  -d "{\"input\": \"${DIGEST_B64}\", \"prehashed\": true, \"hash_algorithm\": \"sha2-256\"}" \
  "${VAULT_ADDR}/v1/transit/sign/${KEY_NAME}")

SIGNATURE=$(echo "${SIGNATURE_RESPONSE}" | jq -r '.data.signature')

if [[ -z "${SIGNATURE:-}" || "$SIGNATURE" == "null" ]]; then
  echo "[!] Signing failed. Vault response: ${SIGNATURE_RESPONSE}"
  exit 1
fi

# ===== Tanúsítvány beolvasás =====
CERT_RESPONSE=$(curl -s ${CURL_OPTS} \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  "${VAULT_ADDR}/v1/${KEY_NAME}/data/crt") # Assuming KV v2 mount at KEY_NAME, secret 'crt'

CERT=$(echo "${CERT_RESPONSE}" | jq -r '.data.data.bar') # Assuming PEM data is under 'bar' key

if [[ -z "${CERT:-}" || "$CERT" == "null" ]]; then
  echo "[!] CERT get failed. Vault response: ${CERT_RESPONSE}"
  exit 1
fi

# ===== Metaadat blokk hozzáfűzése =====
{
  echo ""
  echo "---"
  echo "[signing-metadata]"
  echo "key = $KEY_NAME"
  echo "signature = $SIGNATURE"
  echo "hash-algorithm = sha256"
  echo "digest = $DIGEST_B64"
  echo ""
  echo "[certificate]"
  echo "$CERT"
} >> "$COMMIT_MSG_FILE"

echo "[*] Commit message updated with signing metadata."
