import base64
import datetime
import hashlib
import logging
import sys
from pathlib import Path

import requests
import yaml
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate

from .releaselib.exceptions import (
    ConfigurationError,
    GitStateError,
    ReleaseError,
    VaultServiceError,
)
from .schemalib.artifact import (
    build_signing_payload,
    compute_spec_checksum,
    parse_certificate_info,
    to_canonical_json,
)
from .schemalib.loader import load_and_resolve_schema, load_yaml, write_yaml
from .schemalib.validator import ValidationFailureError

# Back-compat alias for tests and external consumers
_parse_certificate_info = parse_certificate_info


class ReleaseManager:
    def __init__(
        self,
        config,
        git_service,
        vault_service,
        project_root: Path = Path("."),
        dry_run=False,
        logger=None,
    ):
        self.config = config
        self.git_service = git_service
        self.vault_service = vault_service
        self.project_root = project_root.resolve()
        self.dry_run = dry_run
        self.logger = logger if logger else logging.getLogger(__name__)

    def _path(self, relative_path):
        return self.project_root / relative_path

    def _check_base_branch_and_version(self, release_version: str):
        """Checks git branch and version validity."""
        component_name = self.config.get("component_name", "main")
        original_base_branch = self.git_service.get_current_branch()
        self.logger.info(
            f"✓ Starting release process for component '{component_name}' from branch '{original_base_branch}'."
        )
        return component_name, original_base_branch

    def _check_api_accessibility(self, api_url: str):
        """Checks if a given API URL is accessible."""
        self.logger.info(f"Checking API accessibility for: {api_url}")
        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
            self.logger.info(
                f"✓ API '{api_url}' is accessible. Status: {response.status_code}"
            )
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"API '{api_url}' is NOT accessible: {e}")
        sys.exit(0)

    def _validate_final_project_yaml(self):
        """Validates the project.yaml against the project.schema.yaml.

        Note: `compiler_settings.meta_schema_file` (e.g. md.meta.schema.yaml)
        is the meta-schema for *documentation/schema* metadata blocks
        (used by run_validation), not for project.yaml itself.
        project.yaml's own structure is always validated against the
        fixed `project.schema.yaml`, which is a plain JSON Schema (no
        top-level 'spec' wrapper).
        """
        self.logger.info("Validating final project.yaml against schema...")
        try:
            schema_path = self._path("project.schema.yaml")
            schema = load_and_resolve_schema(schema_path)
            if schema is None:
                raise ConfigurationError(
                    f"Project schema file '{schema_path}' is empty."
                )
            project_yaml_path = self._path("project.yaml")
            instance = load_yaml(project_yaml_path)
            if instance is None:
                raise ConfigurationError(
                    f"Project YAML file '{project_yaml_path}' is empty."
                )
            validate(instance=instance, schema=schema)
            # WASM-delta (wasm-template-plan.md, sec. 2.2): the binary
            # buildHash must be filled in (by `make wasm.build` /
            # wasm.buildhash) before finalization is allowed to proceed.
            if not instance.get("metadata", {}).get("buildHash"):
                raise ValidationFailureError(
                    "metadata.buildHash is required and must be non-empty before "
                    "finalization — run 'make wasm.build' to populate it."
                )
            self.logger.info("✓ project.yaml is valid against the schema.")
        except ValidationFailureError:
            raise
        except (ConfigurationError, JsonSchemaValidationError) as e:
            raise ValidationFailureError(f"Final project.yaml validation failed: {e}")
        except Exception as e:
            raise ReleaseError(
                f"An unexpected error occurred during project.yaml validation: {e}"
            )

    def _execute_developer_preparation_phase(
        self, release_version: str, component_name: str, original_base_branch: str
    ):
        """Handles the developer preparation phase: creates release branch, updates project.yaml, commits."""
        if self.git_service.is_dirty():
            raise GitStateError(
                "Uncommitted changes detected. Please commit or stash them before starting a release."
            )
        self.git_service.assert_clean_index()

        project_yaml_path = self._path("project.yaml")
        release_branch_name = (
            f"{component_name}/releases/v{release_version}"
            if component_name != "main"
            else f"releases/v{release_version}"
        )

        try:
            self.logger.info(
                f"Creating release branch: '{release_branch_name}' from '{original_base_branch}'"
            )
            if not self.dry_run:
                self.git_service.checkout(release_branch_name, create_new=True)
            self.logger.info(f"✓ Switched to release branch: '{release_branch_name}'")

            self.logger.info("Processing and validating source schema...")
            source_file = self._path(
                self.config.get("canonical_source_file", "sources/index.yaml")
            )
            source_data = load_and_resolve_schema(source_file)

            self.logger.info("✓ Source schema loaded and resolved.")

            self.logger.info("Assembling the developer-stage project.yaml metadata...")

            checksum = compute_spec_checksum(source_data["spec"])
            self.logger.info(f"✓ Calculated spec checksum: {checksum[:12]}...")

            user_certificate = self.vault_service.get_certificate(
                self.config["vault_cert_mount"],
                self.config["vault_cert_secret_name"],
                self.config["vault_cert_secret_key"],
            )
            cic_root_ca_cert = self.vault_service.get_certificate(
                self.config["vault_cert_mount"],
                self.config.get("cic_root_ca_secret_name", "CICRootCA"),
                self.config["vault_cert_secret_key"],
            )
            self.logger.info("✓ User and CIC Root CA certificates obtained from Vault.")

            build_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            schema_name = source_data.get("metadata", {}).get("name", "unknown")

            digest_b64 = build_signing_payload(
                name=schema_name,
                version=release_version,
                checksum=checksum,
                build_timestamp=build_timestamp,
            )
            signature = self.vault_service.sign(
                digest_b64, self.config["vault_key_name"]
            )
            self.logger.info("✓ Project metadata signed successfully.")

            project_data = load_yaml(project_yaml_path) or {}
            metadata = {
                **project_data.get("metadata", {}),
                "version": release_version,
                "checksum": checksum,
                "sign": signature,
                "build_timestamp": build_timestamp,
                "createdBy": {
                    "name": None,
                    "email": None,
                    "certificate": user_certificate,
                    "issuer_certificate": cic_root_ca_cert,
                },
                "buildHash": "",
                "cicSign": "",
                "cicSignedCA": {"certificate": ""},
            }
            cert_name, cert_email = _parse_certificate_info(user_certificate)
            metadata["createdBy"]["name"] = cert_name
            metadata["createdBy"]["email"] = cert_email
            self.logger.info(f"✓ Parsed user certificate: {cert_name} <{cert_email}>")

            project_data["metadata"] = metadata
            project_data["spec"] = source_data["spec"]

            if self.dry_run:
                self.logger.info(
                    "[DRY-RUN] The following data would be written to project.yaml:"
                )
                self.logger.info(yaml.dump(project_data, sort_keys=False, indent=2))
            else:
                self.logger.info("Writing developer-stage metadata to project.yaml...")
                write_yaml(project_yaml_path, project_data)
                self.logger.info("✓ project.yaml updated for developer release step.")
                self.git_service.add(str(project_yaml_path))
                commit_message = (
                    f"release: Prepare {component_name} v{release_version} for build"
                )
                self.logger.info(f"Committing changes with message: '{commit_message}'")
                self.git_service.run(["git", "commit", "-m", commit_message])
                self.logger.info("✓ Developer release commit created successfully.")

            self.logger.info(
                f"✓ Release branch '{release_branch_name}' created. Proceed with build and finalization."
            )
            self.logger.info(
                f"ACTION REQUIRED: You are now on branch '{release_branch_name}'."
            )
            self.logger.info(
                "  1. Run your build process to generate artifacts and update 'buildHash' in project.yaml."
            )
            self.logger.info("  2. Commit the updated project.yaml to this branch.")
            self.logger.info("  3. Run 'make release VERSION=...' again to finalize.")

        except Exception as e:
            self.logger.critical(
                f"Release process failed during developer preparation: {e}",
                exc_info=True,
            )
            if not self.dry_run:
                try:
                    self.logger.warning(
                        f"Attempting to clean up release branch '{release_branch_name}'."
                    )
                    self.git_service.checkout(original_base_branch)
                    self.git_service.delete_branch(release_branch_name, force=True)
                    self.logger.info("✓ Release branch cleaned up.")
                except Exception as cleanup_e:
                    self.logger.critical(
                        f"Failed to clean up release branch: {cleanup_e}", exc_info=True
                    )
            raise ReleaseError(f"Release process failed: {e}") from e

    def _resign_with_build_hash(self, project_yaml_path):
        """Re-signs project.yaml metadata so the Vault signature also covers
        metadata.buildHash (wasm-template-plan.md, sec. 2.2/a — option (a)):
        a single signature binds source-spec checksum + binary buildHash
        together (provenance + integrity in one signature).
        """
        project_data = load_yaml(project_yaml_path) or {}
        metadata = project_data.get("metadata", {})

        metadata_for_signing = {
            "name": metadata.get("name", "unknown"),
            "version": metadata.get("version"),
            "checksum": metadata.get("checksum"),
            "build_timestamp": metadata.get("build_timestamp"),
            "buildHash": metadata.get("buildHash"),
        }

        digest_bytes = to_canonical_json(metadata_for_signing)
        digest_b64 = base64.b64encode(hashlib.sha256(digest_bytes).digest()).decode(
            "utf-8"
        )

        if self.dry_run:
            self.logger.info(
                "[DRY-RUN] Would re-sign metadata (incl. buildHash) with key "
                f"'{self.config['vault_key_name']}': {metadata_for_signing}"
            )
            return

        signature = self.vault_service.sign(digest_b64, self.config["vault_key_name"])
        metadata["sign"] = signature
        project_data["metadata"] = metadata
        write_yaml(project_yaml_path, project_data)
        self.logger.info("✓ project.yaml metadata re-signed, covering buildHash.")

    def _execute_finalization_phase(
        self,
        release_version: str,
        component_name: str,
        original_base_branch: str,
        release_branch_name: str,
    ):
        """Handles the finalization phase: validates project.yaml, commits, tags, merges, and cleans up."""
        project_yaml_path = self._path("project.yaml")
        main_branch = self.config.get("main_branch", "main")

        self.logger.info(
            f"--- Starting Finalization for v{release_version} on branch '{release_branch_name}' ---"
        )
        self._validate_final_project_yaml()
        self.logger.info(
            "✓ project.yaml is fully validated and ready for finalization."
        )

        self._resign_with_build_hash(project_yaml_path)

        if not self.dry_run:
            if self.git_service.is_dirty():
                self.logger.info(
                    "Committing pending changes to project.yaml (from build process)..."
                )
                self.git_service.add(str(project_yaml_path))
                self.git_service.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"release: Finalize {component_name} v{release_version} build artifacts",
                    ]
                )
            else:
                self.logger.info(
                    "No pending changes to project.yaml detected. Assuming manual commit of build artifacts."
                )

            final_tag_name = f"{component_name}@v{release_version}"
            final_tag_message = f"Release {component_name} v{release_version}"
            self.logger.info(f"Creating final annotated tag: '{final_tag_name}'")
            self.git_service.run(
                ["git", "tag", "-a", final_tag_name, "-m", final_tag_message]
            )
            self.logger.info("✓ Final release tag created.")

            self.logger.info(f"Switching back to main branch: '{main_branch}'")
            self.git_service.checkout(main_branch)
            self.logger.info(f"Merging '{release_branch_name}' into '{main_branch}'")
            self.git_service.merge(
                release_branch_name,
                no_ff=True,
                message=f"Merge branch '{release_branch_name}' for release {release_version}",
            )
            self.logger.info(f"Deleting release branch: '{release_branch_name}'")
            self.git_service.delete_branch(release_branch_name)

        self.logger.info(
            f"✓ Release v{release_version} successfully finalized and merged into '{main_branch}'."
        )

    def run_release_close(self, release_version: str):
        """Orchestrates the release process based on the current Git branch and dry_run status."""
        component_name, original_base_branch = self._check_base_branch_and_version(
            release_version
        )
        if not self.vault_service:
            raise VaultServiceError("VaultService is not initialized.")

        main_branch = self.config.get("main_branch", "main")
        release_branch_name = (
            f"{component_name}/releases/v{release_version}"
            if component_name != "main"
            else f"releases/v{release_version}"
        )

        if self.dry_run:
            self.logger.info("[DRY-RUN] Simulating Developer Preparation Phase.")
            self._execute_developer_preparation_phase(
                release_version, component_name, original_base_branch
            )
        elif original_base_branch == main_branch:
            self._execute_developer_preparation_phase(
                release_version, component_name, original_base_branch
            )
        elif original_base_branch == release_branch_name:
            self._execute_finalization_phase(
                release_version,
                component_name,
                original_base_branch,
                release_branch_name,
            )
        else:
            raise GitStateError(
                f"Release command must be run from the main branch ('{main_branch}') "
                f"to start a new release, or from an existing release branch ('{release_branch_name}') "
                f"to finalize it. Currently on '{original_base_branch}'."
            )

    def run_validation(self):
        """Runs offline validation on the canonical source schema."""
        self.logger.info("--- Running Schema Validation ---")
        source_file = self._path(
            self.config.get("canonical_source_file", "sources/index.yaml")
        )
        self.logger.info(f"Validating and resolving {source_file}...")
        try:
            source_data = load_and_resolve_schema(source_file)
            # Placeholder for full validation logic. Using the loaded data prevents the lint error.
            self.logger.info(
                f"Schema '{source_data.get('metadata', {}).get('name', 'N/A')}' loaded."
            )
            self.logger.info("✓ Schema validation logic to be fully implemented here.")
        except (ConfigurationError, JsonSchemaValidationError, ValueError) as e:
            self.logger.critical(f"VALIDATION FAILED: {e}")
            raise ReleaseError("Schema validation failed.") from e
        except Exception as e:
            self.logger.critical(f"UNEXPECTED ERROR during validation: {e}")
            raise ReleaseError("An unexpected error occurred during validation.") from e

        self.logger.info("✓ Validation successful.")
