#!/usr/bin/env python3
# finalize_release.py - Finalizes and signs a release YAML file.
#
# Copyright (c) 2025, Gábor Zoltán Sinkó
# Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License
# See https://creativecommons.org/licenses/by-nc-sa/4.0/

# FIXME: This script is a temporary solution for the finalization and central
# signing of a release. It is intended to be used until a secure, closed-source
# build environment ("relay") and a central signing API are available.
#
# The final workflow will be orchestrated by `compiler.py`, which will call the
# central API to perform the build and signing steps in a trusted environment.
# Once that system is in place, this script will become obsolete and should be
# removed.

# DEPRECATED: This module is dead code on the production release path
# (no Makefile/mk/*.mk/.github/workflows/*.yml call site — verified via
# `grep -rn "finalize_release"`). The active release chain is
# `make release` -> tools.compiler -> tools.infra.ReleaseManager
# (see tools/infra.py:254-287 for the checksum+buildHash signing model).
# Track relay-readiness as a separate milestone; delete this module on
# relay GA (cf. CIC-Schemas compiler-architecture-plan.md, "Step 10").

import argparse
import base64
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

import yaml

# Assuming the script is run from the project root, so 'tools' is in the path.
# This allows us to import from our own library.
from .releaselib.exceptions import VaultServiceError
from .releaselib.vault_service import VaultService

# --- Logging Setup ---
LOG_FORMAT = "%(levelname)s: %(message)s"
COLOR_CODES = {
    "DEBUG": "\033[90m",
    "INFO": "\033[0m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[91m",
    "SUCCESS": "\033[92m",
}
RESET_CODE = "\033[0m"


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_message = super().format(record)
        color_code = COLOR_CODES.get(record.levelname, RESET_CODE)
        if "✓" in log_message:
            color_code = COLOR_CODES["SUCCESS"]
        return f"{color_code}{log_message}{RESET_CODE}"


def setup_logging(verbose=False, debug=False):
    """Sets up colored logging."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter(LOG_FORMAT))
        logger.addHandler(handler)

    log_level = (
        logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    )
    logger.handlers[0].setLevel(log_level)
    logger.propagate = False
    return logger


logger = logging.getLogger(__name__)


# --- YAML and Hashing Helpers ---
def load_yaml(path: Path):
    """Loads a YAML file with error handling."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (IOError, yaml.YAMLError) as e:
        logger.critical(f"Error loading YAML file {path}: {e}")
        raise


def write_yaml(path: Path, data):
    """Writes data to a YAML file with error handling."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, indent=2, allow_unicode=True)
    except IOError as e:
        logger.critical(f"Error writing YAML file {path}: {e}")
        raise


def get_canonical_hash(data: dict) -> str:
    """Creates a reproducible, base64-encoded SHA256 hash of a dictionary."""
    canonical_string = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    hasher = hashlib.sha256()
    hasher.update(canonical_string.encode("utf-8"))
    digest = hasher.digest()
    return base64.b64encode(digest).decode("utf-8")


def main():
    """Main execution logic."""
    parser = argparse.ArgumentParser(
        description="Finalize and sign a release YAML file using a CIC Vault key.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "filepath", type=Path, help="Path to the project.yaml file to finalize."
    )
    parser.add_argument(
        "--cic-vault-key",
        required=True,
        help="Name of the CIC Vault key for signing (e.g., 'cic-root-ca-key').",
    )

    cert_group = parser.add_mutually_exclusive_group(required=True)
    cert_group.add_argument(
        "--cic-cert-file",
        type=Path,
        help="Path to the file containing the CIC CA certificate to embed.",
    )
    cert_group.add_argument(
        "--cic-cert-vault-path",
        help="Vault path to the certificate, e.g., 'kv/data/secrets/my-cert:cert_key'.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a trial run without writing the file.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug output (most verbose)."
    )

    args = parser.parse_args()

    global logger
    logger = setup_logging(args.verbose, args.debug)

    try:
        # --- Pre-flight Checks ---
        if not args.filepath.exists():
            raise FileNotFoundError(
                f"The specified file was not found: {args.filepath}"
            )
        if args.cic_cert_file and not args.cic_cert_file.exists():
            raise FileNotFoundError(
                f"The CIC certificate file was not found: {args.cic_cert_file}"
            )

        # --- Vault Service Initialization ---
        vault_addr = os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT_TOKEN")
        vault_cacert = os.getenv("VAULT_CACERT")

        if not vault_addr or not vault_token:
            raise VaultServiceError(
                "VAULT_ADDR and VAULT_TOKEN environment variables must be set."
            )

        vault_service = VaultService(
            vault_addr=vault_addr,
            vault_token=vault_token,
            vault_cacert=vault_cacert,
            dry_run=args.dry_run,
            logger=logger,
        )

        # --- Main Logic ---
        logger.info(f"Starting finalization for: {args.filepath}")
        project_data = load_yaml(args.filepath)
        metadata = project_data.get("metadata")

        if not metadata:
            raise ValueError("The 'metadata' block was not found in the YAML file.")

        # 1. Validation Step
        logger.info("Validating checksum against buildHash...")
        checksum = metadata.get("checksum")
        build_hash = metadata.get("buildHash")
        logger.debug(f"  - Checksum: {checksum}")
        logger.debug(f"  - BuildHash: {build_hash}")

        if not checksum or not build_hash:
            raise ValueError(
                "'checksum' and/or 'buildHash' fields are missing from metadata."
            )
        if checksum != build_hash:
            raise ValueError(
                "Validation failed: 'checksum' and 'buildHash' do not match!"
            )

        logger.info("✓ Validation successful: checksum matches buildHash.")

        # 2. Embed CIC Certificate
        if args.cic_cert_vault_path:
            logger.info(
                f"Fetching CIC certificate from Vault path: {args.cic_cert_vault_path}..."
            )
            try:
                path_parts = args.cic_cert_vault_path.split(":")
                if len(path_parts) != 2:
                    raise ValueError(
                        "Vault path must be in the format 'mount/path/to/secret:key'"
                    )

                full_secret_path, secret_key = path_parts
                mount_path, secret_name = full_secret_path.split("/data/", 1)
                mount_path += "/data"

                cic_certificate = vault_service.get_certificate(
                    mount_path, secret_name, secret_key
                )
            except (ValueError, VaultServiceError) as e:
                raise VaultServiceError(
                    f"Could not retrieve certificate from Vault: {e}"
                ) from e
        else:
            logger.info(f"Embedding CIC certificate from {args.cic_cert_file}...")
            with open(args.cic_cert_file, "r", encoding="utf-8") as f:
                cic_certificate = f.read()

        metadata.setdefault("cicSignedCA", {})["certificate"] = cic_certificate
        logger.info("✓ 'cicSignedCA.certificate' field updated.")

        # 3. Prepare for Signing
        # The signature must cover the final state, including the embedded CA cert.
        # We temporarily clear the target field to generate the hash.
        metadata["cicSign"] = ""

        logger.info("Generating canonical hash of the final document for signing...")
        hash_to_sign = get_canonical_hash(project_data)
        logger.debug(f"  - Hash to be signed (b64): {hash_to_sign}")

        logger.info(
            f"Requesting signature from Vault with key '{args.cic_vault_key}'..."
        )
        cic_signature = vault_service.sign(hash_to_sign, args.cic_vault_key)
        logger.info("✓ Signature received successfully from Vault.")

        # 4. Embed Final Signature
        metadata["cicSign"] = cic_signature

        # 5. Write Final File
        if args.dry_run:
            logger.info("\n--- DRY-RUN: Final YAML content ---")
            print(
                yaml.dump(project_data, sort_keys=False, indent=2, allow_unicode=True)
            )
            logger.info("--- End of DRY-RUN ---")
        else:
            logger.info(f"Writing finalized and signed data back to {args.filepath}...")
            write_yaml(args.filepath, project_data)
            logger.info(f"✓ Finalization complete. {args.filepath} has been updated.")

    except (ValueError, VaultServiceError, IOError, FileNotFoundError) as e:
        logger.critical(f"[FAILURE] The finalization process failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"[UNEXPECTED ERROR] An unhandled exception occurred: {e}",
            exc_info=logger.level == logging.DEBUG,
        )
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    # This allows the script to be run with `python -m tools.finalize_release ...`
    # which correctly handles the relative imports.
    main()
