#!/usr/bin/env bash
set -euo pipefail

# Run on the Vault VM (cic-poc-vault).
# Starts Vault in dev (in-memory) mode and configures the Transit engine
# with the cic-relay-signing key used for ProofTrace signing
# (system-plan.md 1.3).

VAULT_DEV_ROOT_TOKEN_ID="${VAULT_DEV_ROOT_TOKEN_ID:-cic-poc-root-token}"
VAULT_LISTEN_ADDR="${VAULT_LISTEN_ADDR:-0.0.0.0:8200}"

echo "Starting Vault dev server on ${VAULT_LISTEN_ADDR} ..."
nohup vault server -dev \
  -dev-listen-address="${VAULT_LISTEN_ADDR}" \
  -dev-root-token-id="${VAULT_DEV_ROOT_TOKEN_ID}" \
  > /var/log/vault-dev.log 2>&1 &

export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID}"

until vault status >/dev/null 2>&1; do
  echo "waiting for vault to come up..."
  sleep 1
done

echo "Enabling transit secrets engine ..."
vault secrets enable transit || echo "transit already enabled"

echo "Creating cic-relay-signing transit key ..."
vault write -f transit/keys/cic-relay-signing

echo "Vault dev mode ready."
echo "VAULT_ADDR=${VAULT_ADDR}"
echo "VAULT_TOKEN=${VAULT_TOKEN}"
echo "Note: mem mode -> root token is static and key material is lost on restart"
echo "(scaffold per relay-func-audit, accepted for the PoC)."
