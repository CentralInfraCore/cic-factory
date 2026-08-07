import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

from .infra import ReleaseManager
from .releaselib.exceptions import ManualInterventionRequired, ReleaseError
from .releaselib.git_service import GitService
from .releaselib.vault_service import VaultService

# --- Logging Setup ---
LOG_FORMAT = "%(levelname)s: %(message)s"
COLOR_CODES = {
    "DEBUG": "\033[90m",
    "INFO": "\033[0m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[91m",
    "DRY_RUN": "\033[96m",
    "SUCCESS": "\033[92m",
    "MANUAL": "\033[94m",
}
RESET_CODE = "\033[0m"


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_message = super().format(record)
        level_name = record.levelname

        if "DRY-RUN" in log_message:
            level_name = "DRY_RUN"
        elif "ACTION REQUIRED" in log_message:
            level_name = "MANUAL"
        elif "✓" in log_message:
            level_name = "SUCCESS"

        color_code = COLOR_CODES.get(level_name, RESET_CODE)
        return f"{color_code}{log_message}{RESET_CODE}"


def setup_logging(verbose=False, debug=False):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)

    handler = logger.handlers[0]
    handler.setLevel(
        logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    )
    logger.propagate = False
    return logger


logger = logging.getLogger(__name__)


# --- Configuration Loader ---
def load_project_config():
    try:
        with open("project.yaml", "r") as f:
            config = yaml.safe_load(f)
            if "compiler_settings" not in config:
                raise KeyError("'compiler_settings' not found in project.yaml")
            return config
    except (IOError, KeyError, TypeError, yaml.YAMLError) as e:
        logger.critical(f"[FATAL] Could not load or parse project.yaml: {e}")
        sys.exit(1)


# --- Main Application Logic ---
def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--dry-run", action="store_true", help="Perform a trial run."
    )
    parent_parser.add_argument(
        "--git-timeout", type=int, default=60, help="Timeout for Git commands."
    )
    parent_parser.add_argument(
        "--vault-timeout", type=int, default=10, help="Timeout for Vault API calls."
    )
    parent_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )
    parent_parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug output."
    )

    parser = argparse.ArgumentParser(
        description="Schema Compiler & Release Tool", parents=[parent_parser]
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    subparsers.add_parser(
        "validate", help="Validate all schemas.", parents=[parent_parser]
    )

    release_parser = subparsers.add_parser(
        "release", help="Prepare or finalize a release.", parents=[parent_parser]
    )
    release_parser.add_argument(
        "--version",
        required=True,
        help="The semantic version to release (e.g., 1.0.0).",
    )

    build_hash_parser = subparsers.add_parser(
        "set-build-hash",
        help="Compute sha256(artifact) and write it to project.yaml metadata.buildHash.",
        parents=[parent_parser],
    )
    build_hash_parser.add_argument(
        "--file", required=True, help="Path to the build artifact (e.g. module.wasm)."
    )
    build_hash_parser.add_argument(
        "--project", default="project.yaml", help="Path to project.yaml."
    )

    args = parser.parse_args()

    global logger
    logger = setup_logging(args.verbose, args.debug)

    if args.command == "set-build-hash":
        # stdlib-only: hashlib + a targeted regex edit of the metadata.buildHash
        # line. Deliberately avoids importing tools.infra (and its pyyaml/
        # requests/jsonschema deps) so this command works even before the
        # builder's p_venv cache (infra.deps) has been populated.
        import hashlib
        import re

        artifact = Path(args.file)
        project_yaml_path = Path(args.project)
        if not artifact.is_file():
            logger.critical(f"[FATAL] Artifact not found: {artifact}")
            sys.exit(1)

        build_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()

        content = project_yaml_path.read_text(encoding="utf-8")
        pattern = re.compile(r"^(\s*buildHash:\s*).*$", re.MULTILINE)
        if not pattern.search(content):
            logger.critical(
                f"[FATAL] metadata.buildHash field not found in {project_yaml_path}"
            )
            sys.exit(1)
        content = pattern.sub(rf"\g<1>{build_hash}", content, count=1)
        project_yaml_path.write_text(content, encoding="utf-8")

        logger.info(f"✓ metadata.buildHash = {build_hash}")
        return

    try:
        if args.dry_run:
            logger.info("--- Starting in DRY-RUN mode. No changes will be made. ---")

        full_config = load_project_config()
        compiler_config = full_config.get("compiler_settings", {})

        project_root = Path(os.getcwd())
        git_service = GitService(cwd=project_root, timeout=args.git_timeout)

        vault_addr = os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT_TOKEN")
        vault_token_file = os.getenv(
            "CIC_VAULT_TOKEN_FILE", "/var/run/secrets/vault-token"
        )
        if not vault_token and os.path.exists(vault_token_file):
            try:
                with open(vault_token_file, "r") as f:
                    vault_token = f.read().strip()
            except IOError as e:
                logger.warning(
                    f"Could not read Vault token from {vault_token_file}: {e}"
                )

        vault_cacert = os.getenv("VAULT_CACERT")
        vault_cacert_file = "/var/run/secrets/vault-ca.crt"
        if not vault_cacert and os.path.exists(vault_cacert_file):
            vault_cacert = vault_cacert_file

        vault_service = VaultService(
            vault_addr=vault_addr,
            vault_token=vault_token,
            vault_cacert=vault_cacert,
            dry_run=args.dry_run,
            timeout=args.vault_timeout,
            logger=logger,
        )

        manager = ReleaseManager(
            compiler_config,
            git_service=git_service,
            vault_service=vault_service,
            project_root=project_root,
            dry_run=args.dry_run,
            logger=logger,
        )

        if args.command == "validate":
            logger.info("--- Running Schema Validation ---")
            manager.run_validation()
            logger.info("✓ All schemas are valid.")

        elif args.command == "release":
            manager.run_release_close(release_version=args.version)

    except ManualInterventionRequired as e:
        logger.info(f"[ACTION REQUIRED] {e}")
        sys.exit(0)  # Exit with 0 for manual intervention
    except ReleaseError as e:
        logger.critical(f"[RELEASE FAILED] {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"[UNEXPECTED ERROR] An unhandled exception occurred: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
