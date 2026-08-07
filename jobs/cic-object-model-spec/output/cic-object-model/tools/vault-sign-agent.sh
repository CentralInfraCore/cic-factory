#!/bin/bash
# vault-runner.sh - Temporary Vault signing server launcher
#
# Copyright (c) 2025, Gábor Zoltán Sinkó
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License
# See https://creativecommons.org/licenses/by-nc-sa/4.0/

set -e

KEYFILE=""
ROOT_CA_FILE=""
KEY_NAME="cic-my-sign-key"

show_help() {
  echo "Usage: $0 [OPTIONS]"
  echo "  -k, --keyfile <file>      Encrypted private key file"
  echo "  -c, --crtfile <file>      Public certificate file (crt format)"
  echo "  --root-ca-file <file>   Public Root CA certificate file (crt format)"
  echo "  -n, --name <key-name>     Vault key name (default: cic-my-sign-key)"
  echo "  -s, --stop                Stop the running Vault server"
  echo "  -h, --help                Display this help message"
  exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -k|--keyfile)
      KEYFILE="$2"
      shift 2
      ;;
    -c|--crtfile)
      CRTFILE="$2"
      shift 2
      ;;
    --root-ca-file)
      ROOT_CA_FILE="$2"
      shift 2
      ;;
    -n|--name)
      KEY_NAME="$2"
      shift 2
      ;;
    -s|--stop|stop)
      STOP=1
      shift
      ;;
    -h|--help)
      show_help
      ;;
    *)
      echo "[!] Unknown option: $1"
      show_help
      ;;
  esac
done

if [[ "$STOP" == "1" ]]; then
  if [[ -f $XDG_RUNTIME_DIR/vault/vault.pid ]]; then
    kill $(cat $XDG_RUNTIME_DIR/vault/vault.pid) && echo "[*] Vault stopped." && rm -f $XDG_RUNTIME_DIR/vault/vault.pid
  else
    echo "[!] vault.pid file not found – is Vault running?"
  fi
  exit 0
fi


if [[ -f $XDG_RUNTIME_DIR/vault/vault.pid ]]; then
  echo "[!] vault.pid file found – is Vault running? First stop the vault"
  exit 0
fi

TMPDIR=$(mktemp -d)
VAULT_PORT=18200
TOKEN_FILE="$XDG_RUNTIME_DIR/vault/sign-token"
SERVER_CA_FILE="$XDG_RUNTIME_DIR/vault/server.crt" # New file for server CA cert
VAULT_KEY="$TMPDIR/vault-key.pem"
VAULT_CERT="$TMPDIR/vault-cert.pem"
PIDFILE="vault.pid"
export VAULT_API_ADDR="https://127.0.0.1:$VAULT_PORT"
export VAULT_ADDR="https://127.0.0.1:$VAULT_PORT"
mkdir -p $XDG_RUNTIME_DIR/vault

if [[ -z "$KEYFILE" || -z "$CRTFILE" || -z "$ROOT_CA_FILE" ]]; then
  echo "[!] Key file, certificate file, and Root CA file must all be specified."
  show_help
fi

read -s -p "Enter private key password (hidden input): " KEYPASS
echo

# Create SAN config for self-signed cert
cat > "$TMPDIR/san.cnf" <<EOF
[req]
distinguished_name=req_distinguished_name
req_extensions=SAN
prompt=no

[req_distinguished_name]
CN=localhost

[SAN]
subjectAltName=DNS:localhost,IP:127.0.0.1,DNS:host.docker.internal
EOF

# Generate self-signed certificate
echo "[*] Generating Vault HTTPS certificate..."
openssl req -x509 -nodes -newkey rsa:2048 -keyout "$VAULT_KEY" -out "$VAULT_CERT" -days 365 -config "$TMPDIR/san.cnf" -extensions SAN

# Copy the generated server certificate to the well-known location for Docker mounting
cp "$VAULT_CERT" "$SERVER_CA_FILE"
echo "[*] Vault server CA certificate saved to: $SERVER_CA_FILE"

# Set VAULT_CACERT for the vault CLI to trust the self-signed cert
export VAULT_CACERT="$SERVER_CA_FILE"

# Create Vault config and start server
echo "[*] Starting Vault server..."
cat > "$TMPDIR/vault-config.hcl" <<EOF
listener "tcp" {
  address     = "0.0.0.0:$VAULT_PORT"
  tls_disable = 0
  tls_cert_file = "$VAULT_CERT"
  tls_key_file  = "$VAULT_KEY"
}
storage "inmem" {}
disable_mlock = true
ui = false
EOF

nohup vault server -config="$TMPDIR/vault-config.hcl" > "$TMPDIR/vault.log" 2>&1 &
echo $! > "$XDG_RUNTIME_DIR/vault/$PIDFILE"
VAULT_PID=$(cat "$XDG_RUNTIME_DIR/vault/$PIDFILE")

sleep 2

echo "[*] Initializing and unsealing Vault..."
key=$(vault operator init -key-shares=5 -key-threshold=3 -format=json)
for k in $(echo "$key" | jq -r '.unseal_keys_b64[0:3][]'); do
  vault operator unseal "$k"
done
export VAULT_TOKEN=$(echo "$key" | jq -r '.root_token')

sleep 2

vault secrets enable transit

# Import private key into Vault via pipe
echo "[*] Importing private key into Vault..."
vault transit import transit/keys/$KEY_NAME @<(openssl pkey -in "$KEYFILE" -passin pass:"$KEYPASS" \
  | openssl pkcs8 -topk8 -nocrypt -outform der \
  | openssl base64 -A) type=ecdsa-p256

vault secrets enable -path=$KEY_NAME -version=2 kv
echo "[*] Storing public certificate in Vault..."
cat "$CRTFILE" | vault kv put -mount=$KEY_NAME crt bar=-

echo "[*] Storing Root CA certificate in Vault..."
cat "$ROOT_CA_FILE" | vault kv put -mount=$KEY_NAME CICRootCA bar=-

# Create sign policy
cat > "$TMPDIR/sign-policy.hcl" <<EOF
path "transit/sign/$KEY_NAME" {
  capabilities = ["update"]
}
path "$KEY_NAME/data/crt" {
  capabilities = ["read"]
}
path "$KEY_NAME/data/CICRootCA" {
  capabilities = ["read"]
}
EOF
vault policy write sign-policy "$TMPDIR/sign-policy.hcl"

# Create and store token
SIGN_TOKEN=$(vault token create -policy="sign-policy" -format=json | jq -r .auth.client_token)
echo "$SIGN_TOKEN" > "$TOKEN_FILE"

echo "[*] Signing token created: $TOKEN_FILE"
echo "[*] Vault server CA certificate saved to: $SERVER_CA_FILE"
echo "[*] VAULT_ADDR: $VAULT_ADDR"
echo "[*] Vault PID: $VAULT_PID"
echo "[*] Stop Vault: $0 --stop"

#trap "rm -rf $TMPDIR" EXIT

# ---
# This script is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# You may use, adapt, and share it for non-commercial purposes with attribution,
# and you must distribute your modifications under the same license.
#
# License details: https://creativecommons.org/licenses/by-nc-sa/4.0/
