import base64
import logging
import os

import requests

from .exceptions import VaultServiceError


class VaultService:
    """
    A service class to abstract Vault operations, including signing and secret retrieval.
    """

    def __init__(
        self,
        vault_addr,
        vault_token,
        vault_cacert=None,
        dry_run=False,
        timeout=10,
        logger=None,
    ):
        self.dry_run = dry_run
        self.timeout = timeout
        self.logger = logger if logger else logging.getLogger(__name__)

        if not self.dry_run:
            if not vault_addr or not vault_token:
                raise VaultServiceError(
                    "Vault address and token must be provided for a live run."
                )

            if vault_cacert:
                if not os.path.exists(vault_cacert):
                    raise VaultServiceError(
                        f"Provided Vault CA certificate file not found: {vault_cacert}"
                    )
                self.verify_tls = vault_cacert
            else:
                self.verify_tls = True

        self.vault_addr = vault_addr
        self.vault_token = vault_token
        if self.dry_run:
            self.verify_tls = True

    def sign(self, digest_b64, key_name):
        """
        Signs a pre-hashed, base64-encoded digest using Vault's Transit Engine.
        """
        if self.dry_run:
            self.logger.info(
                "[DRY-RUN] Skipping Vault signing. Returning a placeholder signature."
            )
            return "vault:v1:dry-run-placeholder-signature"

        try:
            decoded_digest = base64.b64decode(digest_b64, validate=True)
            if len(decoded_digest) != 32:
                self.logger.warning(
                    f"Digest length is not 32 bytes (SHA256 expected), got {len(decoded_digest)}."
                )
        except (TypeError, ValueError) as e:
            raise VaultServiceError(f"Invalid Base64 digest format: {e}") from e

        response = None
        try:
            self.logger.debug(
                f"Requesting signature from Vault at {self.vault_addr} for key {key_name}..."
            )
            response = requests.post(
                f"{self.vault_addr}/v1/transit/sign/{key_name}",
                headers={"X-Vault-Token": self.vault_token},
                json={
                    "input": digest_b64,
                    "prehashed": True,
                    "hash_algorithm": "sha2-256",
                },
                verify=self.verify_tls,
                timeout=self.timeout,
            )
            response.raise_for_status()

            response_data = response.json()
            signature = response_data.get("data", {}).get("signature")

            if (
                not signature
                or not isinstance(signature, str)
                or not signature.startswith("vault:v1:")
            ):
                raise VaultServiceError(
                    f"Invalid or missing signature in Vault response. Raw response: {response.text}"
                )
            self.logger.debug("Signature received successfully.")
            return signature
        except requests.exceptions.RequestException as e:
            raise VaultServiceError(f"Vault signing request failed: {e}", cause=e)
        except ValueError as e:
            raw_response_text = (
                response.text if response else "No response text available."
            )
            raise VaultServiceError(
                f"Invalid JSON in Vault response: {e}. Raw response: {raw_response_text}",
                cause=e,
            )
        except (AttributeError, KeyError, TypeError) as e:
            raw_response_text = (
                response.text if response else "No response text available."
            )
            raise VaultServiceError(
                f"Could not parse signature from Vault response: {e}. Raw response: {raw_response_text}",
                cause=e,
            )

    def get_certificate(self, mount_path: str, secret_name: str, secret_key: str):
        """
        Retrieves a certificate (or any secret) from Vault's KV v2 engine.
        In dry-run mode, returns a placeholder certificate.
        """
        if self.dry_run:
            self.logger.info(
                "[DRY-RUN] Skipping Vault KV retrieval. Returning a placeholder certificate."
            )
            return "-----BEGIN CERTIFICATE-----\nDRY-RUN-PLACEHOLDER\n-----END CERTIFICATE-----"

        api_path = f"{self.vault_addr}/v1/{mount_path}/data/{secret_name}"

        response = None
        try:
            self.logger.debug(
                f"Requesting secret '{secret_name}' from Vault KV mount at '{mount_path}'..."
            )
            response = requests.get(
                api_path,
                headers={"X-Vault-Token": self.vault_token},
                verify=self.verify_tls,
                timeout=self.timeout,
            )
            response.raise_for_status()

            response_data = response.json()

            certificate = response_data.get("data", {}).get("data", {}).get(secret_key)

            if not certificate or not isinstance(certificate, str):
                raise VaultServiceError(
                    f"Secret key '{secret_key}' not found or is not a string in Vault response. Raw response: {response.text}"
                )

            self.logger.debug(
                f"Secret '{secret_key}' from '{secret_name}' retrieved successfully."
            )
            return certificate
        except requests.exceptions.RequestException as e:
            raise VaultServiceError(f"Vault KV request failed: {e}", cause=e)
        except ValueError as e:
            raw_response_text = (
                response.text if response else "No response text available."
            )
            raise VaultServiceError(
                f"Invalid JSON in Vault KV response: {e}. Raw response: {raw_response_text}",
                cause=e,
            )
        except (AttributeError, KeyError, TypeError) as e:
            raw_response_text = (
                response.text if response else "No response text available."
            )
            raise VaultServiceError(
                f"Could not parse secret from Vault KV response: {e}. Raw response: {raw_response_text}",
                cause=e,
            )
