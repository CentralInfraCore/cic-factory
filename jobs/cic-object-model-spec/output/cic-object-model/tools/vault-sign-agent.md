# Vault Runner Script - Documentation

*Copyright (c) 2025, Gábor Zoltán Sinkó. The script is licensed under the MIT License, while this documentation is licensed under CC BY-NC-SA 4.0.*

This document describes the usage and functionality of the `Vault Runner Script`, a Bash-based utility designed to launch a temporary Vault server, load a private key for digital signing, and provide a token with signing permissions for transactions.

## Key Features

* Launches a temporary Vault server using in-memory storage (no persistence)
* Sets up HTTPS with a self-signed certificate
* Imports a private signing key and enables Vault's Transit secrets engine
* Creates a signing policy and issues a token with scoped permissions
* Enables secure API-based digital signing operations

---

## Usage

### Basic Command Format

```bash
./vault-runner.sh -k <encrypted-private-key> [-n <vault-key-name>]
```

### Parameters

| Option             | Description                                                       |
|--------------------|-------------------------------------------------------------------|
| `-k`, `--keyfile`  | Path to the encrypted private key file (e.g. .pem or .key format) |
| `-c`, `--crtfile`  | Public certificate file (crt format)                              |
| `-n`, `--name`     | Name for the Vault key (optional, default: `cic-my-sign-key`)     |
| `-s`, `--stop`     | Stops the running Vault server                                    |
| `-h`, `--help`     | Displays help message                                             |

### Example: Starting the Server

```bash
./vault-runner.sh -k my-ec256.key -n user-sign-key
```

### Example: Stopping the Server

```bash
./vault-runner.sh --stop
```

---

## Signing a Payload via API

After the script has successfully launched the Vault server, it initializes and unseals it, enables the Transit secrets engine, and generates a token with permission to sign data. The token is stored at:

```
$XDG_RUNTIME_DIR/vault/sign-token
```

The Vault key is created under:

```
transit/keys/<KEY_NAME>
```

To sign a message digest via Vault's HTTP API:

```bash
curl -s \
  --header "X-Vault-Token: $(cat $XDG_RUNTIME_DIR/vault/sign-token)" \
  --request POST \
  --data '{"input": "<BASE64-ENCODED-DIGEST>"}' \
  $VAULT_ADDR/v1/transit/sign/<KEY_NAME>
```

To generate a digest (SHA-256) and encode it in base64:

```bash
echo -n "Hello World" | openssl dgst -sha256 -binary | openssl base64 -A
```

You can then pass the result as the `input` value in the API request.

---

## Security Considerations

* Vault runs in-memory only; no data is persisted after shutdown
* The private key is temporarily imported and used for signing
* HTTPS is enabled with a self-signed certificate, suitable for development/testing purposes

---

## Error Handling

* The script exits on error (`set -e`)
* If the Vault PID or key file is missing, a warning is displayed
* The private key password is entered securely (hidden input)

---

If you'd like more usage examples or detailed REST API workflows, feel free to request them.

---

## License

* The `vault-runner.sh` script is licensed under the **MIT License** (see below).
* This documentation is licensed under the following:

**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**

> You are free to share and adapt this work for non-commercial purposes, as long as you provide attribution and share any derivatives under the same license.
>
> [https://creativecommons.org/licenses/by-nc-sa/4.0/](https://creativecommons.org/licenses/by-nc-sa/4.0/)
