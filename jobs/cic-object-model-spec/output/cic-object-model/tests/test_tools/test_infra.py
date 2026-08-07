import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.infra import (
    ConfigurationError,
    GitStateError,
    ReleaseError,
    ReleaseManager,
    ValidationFailureError,
    _parse_certificate_info,
    load_and_resolve_schema,
    load_yaml,
)
from tools.releaselib.git_service import GitService
from tools.releaselib.vault_service import VaultService

# --- Test Data ---

VALID_PROJECT_YAML = """
metadata:
  name: base
  buildHash: deadbeef
compiler_settings:
  component_name: base
  main_branch: main
  vault_key_name: user-key
  vault_cert_mount: kv
  vault_cert_secret_name: user-cert
  vault_cert_secret_key: cert
  canonical_source_file: sources/index.yaml
  meta_schema_file: project.schema.yaml
"""

VALID_SOURCE_SCHEMA = """
spec:
  key: value
metadata:
  name: test-schema
"""

VALID_CERT = (
    "-----BEGIN CERTIFICATE-----\nMII... (dummy cert) ...END CERTIFICATE-----\n"
)

# --- Fixtures ---


@pytest.fixture
def mock_git_service(mocker):
    service = mocker.MagicMock(spec=GitService)
    service.get_current_branch.return_value = "main"
    service.is_dirty.return_value = False
    return service


@pytest.fixture
def mock_vault_service(mocker):
    service = mocker.MagicMock(spec=VaultService)
    service.sign.return_value = "dummy-signature"
    service.get_certificate.return_value = VALID_CERT
    return service


@pytest.fixture
def mock_config():
    return yaml.safe_load(VALID_PROJECT_YAML)["compiler_settings"]


# --- Test Classes ---


class TestHelperFunctions:
    def test_load_yaml_empty_file(self, mocker):
        mocker.patch("builtins.open", mocker.mock_open(read_data="  "))
        assert load_yaml(Path("empty.yaml")) is None

    def test_load_and_resolve_schema_yaml_error(self, mocker):
        mocker.patch("builtins.open", mocker.mock_open(read_data=": invalid"))
        with pytest.raises(ConfigurationError, match="YAML parsing error"):
            load_and_resolve_schema("invalid.yaml")

    def test_parse_certificate_info_with_alt_name(self, mocker):
        mock_cert = MagicMock()
        mock_subject = MagicMock()
        mock_subject.CN = "Test User"
        mock_subject.emailAddress = "fallback@email.com"
        mock_cert.get_subject.return_value = mock_subject

        mock_ext = MagicMock()
        mock_ext.get_short_name.return_value = b"subjectAltName"
        mock_ext.__str__.return_value = "DNS:localhost, email:alt@email.com"

        mock_cert.get_extension_count.return_value = 1
        mock_cert.get_extension.return_value = mock_ext

        mocker.patch(
            "tools.schemalib.artifact.crypto.load_certificate", return_value=mock_cert
        )
        name, email = _parse_certificate_info(VALID_CERT)
        assert name == "Test User"
        assert email == "alt@email.com"

    def test_parse_certificate_info_fallback_email(self, mocker):
        mock_cert = MagicMock()
        mock_subject = MagicMock()
        mock_subject.CN = "Test User"
        mock_subject.emailAddress = "fallback@email.com"
        mock_cert.get_subject.return_value = mock_subject
        mock_cert.get_extension_count.return_value = 0  # No extensions

        mocker.patch(
            "tools.schemalib.artifact.crypto.load_certificate", return_value=mock_cert
        )
        name, email = _parse_certificate_info(VALID_CERT)
        assert name == "Test User"
        assert email == "fallback@email.com"


class TestReleaseManager:
    @pytest.fixture
    def manager(self, mock_config, mock_git_service, mock_vault_service, mocker):
        logger = mocker.MagicMock(spec=logging.Logger)
        return ReleaseManager(
            config=mock_config,
            git_service=mock_git_service,
            vault_service=mock_vault_service,
            project_root=Path("/fake/project"),
            dry_run=False,
            logger=logger,
        )

    def test_developer_prep_with_non_main_component(self, manager, mocker):
        """Test branch naming when component_name is not 'main'."""
        manager.config["component_name"] = "my-component"
        mocker.patch("builtins.open", mocker.mock_open(read_data=VALID_SOURCE_SCHEMA))
        mocker.patch("tools.infra.write_yaml")
        mocker.patch(
            "tools.infra._parse_certificate_info",
            return_value=("Test", "test@test.com"),
        )
        mocker.patch("sys.exit")

        manager.run_release_close(release_version="1.0.0")
        manager.git_service.checkout.assert_called_once_with(
            "my-component/releases/v1.0.0", create_new=True
        )

    def test_developer_prep_cleanup_fails(self, manager, mocker):
        """Test when the cleanup process itself fails."""
        mocker.patch(
            "tools.infra.load_and_resolve_schema",
            side_effect=ValueError("Failed to load"),
        )
        manager.git_service.delete_branch.side_effect = GitStateError(
            "Cannot delete branch"
        )

        with pytest.raises(ReleaseError, match="Failed to load"):
            manager.run_release_close(release_version="1.0.0")

        manager.logger.critical.assert_any_call(
            "Failed to clean up release branch: Cannot delete branch", exc_info=True
        )

    def test_finalization_with_dirty_repo(self, manager, mocker):
        """Test finalization phase when the repo is dirty (e.g., from build step)."""
        manager.git_service.get_current_branch.return_value = "base/releases/v1.0.0"
        manager.git_service.is_dirty.return_value = True  # Simulate dirty repo
        mocker.patch(
            "tools.infra.load_yaml", return_value=yaml.safe_load(VALID_PROJECT_YAML)
        )
        mocker.patch("tools.infra.load_and_resolve_schema", return_value={"spec": {}})
        mocker.patch("tools.infra.validate")
        mocker.patch("tools.infra.write_yaml")
        mocker.patch("tools.infra.ReleaseManager._resign_with_build_hash")

        manager.run_release_close(release_version="1.0.0")

        manager.git_service.run.assert_any_call(
            ["git", "commit", "-m", "release: Finalize base v1.0.0 build artifacts"]
        )
        manager.logger.info.assert_any_call(
            "Committing pending changes to project.yaml (from build process)..."
        )

    def test_validate_final_yaml_empty_schema(self, manager, mocker):
        """Test final validation when the schema file is empty."""
        mocker.patch("tools.infra.load_and_resolve_schema", return_value=None)
        with pytest.raises(
            ValidationFailureError, match="Project schema file.*is empty"
        ):
            manager._validate_final_project_yaml()

    def test_validate_final_yaml_empty_instance(self, manager, mocker):
        """Test final validation when the project.yaml file is empty."""
        mocker.patch("tools.infra.load_and_resolve_schema", return_value={"spec": {}})
        mocker.patch("tools.infra.load_yaml", return_value=None)
        with pytest.raises(ValidationFailureError, match="Project YAML file.*is empty"):
            manager._validate_final_project_yaml()

    def test_run_validation_unexpected_error(self, manager, mocker):
        """Test generic exception handling in run_validation."""
        mocker.patch(
            "tools.infra.load_and_resolve_schema",
            side_effect=Exception("Unexpected boom"),
        )
        with pytest.raises(
            ReleaseError, match="An unexpected error occurred during validation"
        ):
            manager.run_validation()
        manager.logger.critical.assert_any_call(
            "UNEXPECTED ERROR during validation: Unexpected boom"
        )

    # This is a re-add of a previously deleted test to ensure coverage of the dry-run path in run_release_close
    def test_dry_run_developer_phase(self, manager, mocker):
        manager.dry_run = True
        mock_write_yaml = mocker.patch("tools.infra.write_yaml")
        mocker.patch("builtins.open", mocker.mock_open(read_data=VALID_SOURCE_SCHEMA))
        mocker.patch(
            "tools.infra._parse_certificate_info",
            return_value=("Test", "test@test.com"),
        )

        manager.run_release_close(release_version="1.0.0")

        mock_write_yaml.assert_not_called()
        manager.git_service.checkout.assert_not_called()
        manager.logger.info.assert_any_call(
            "[DRY-RUN] Simulating Developer Preparation Phase."
        )
        manager.logger.info.assert_any_call(
            "[DRY-RUN] The following data would be written to project.yaml:"
        )

    # The following tests are kept from the previous version to ensure basic paths are still covered
    def test_developer_preparation_phase_success(self, manager, mocker):
        mocker.patch("builtins.open", mocker.mock_open(read_data=VALID_SOURCE_SCHEMA))
        mock_write_yaml = mocker.patch("tools.infra.write_yaml")
        mocker.patch(
            "tools.infra._parse_certificate_info",
            return_value=("Test User", "test@user.com"),
        )
        mocker.patch("sys.exit")

        manager.run_release_close(release_version="1.0.0")

        manager.git_service.checkout.assert_called_once_with(
            "base/releases/v1.0.0", create_new=True
        )
        written_data = mock_write_yaml.call_args[0][1]
        assert written_data["metadata"]["version"] == "1.0.0"

    def test_finalization_phase_success(self, manager, mocker):
        manager.git_service.get_current_branch.return_value = "base/releases/v1.0.0"
        mocker.patch(
            "tools.infra.load_yaml", return_value=yaml.safe_load(VALID_PROJECT_YAML)
        )
        mocker.patch("tools.infra.load_and_resolve_schema", return_value={"spec": {}})
        mocker.patch("tools.infra.validate")
        mocker.patch("tools.infra.write_yaml")
        mocker.patch("tools.infra.ReleaseManager._resign_with_build_hash")

        manager.run_release_close(release_version="1.0.0")

        manager.git_service.run.assert_any_call(
            ["git", "tag", "-a", "base@v1.0.0", "-m", "Release base v1.0.0"]
        )
        manager.git_service.checkout.assert_called_once_with("main")

    def test_invalid_branch_fails(self, manager):
        manager.git_service.get_current_branch.return_value = "feature/other"
        with pytest.raises(
            GitStateError, match="Release command must be run from the main branch"
        ):
            manager.run_release_close(release_version="1.0.0")


# --- Mock-free _validate_final_project_yaml tests against the real schema ---
#
# These run the real `load_and_resolve_schema`/`load_yaml`/`validate` code
# path against the repository's actual project.schema.yaml, to guard
# against the schema["spec"] vs. meta_schema_file mismatch that previously
# made finalization raise a KeyError on every real run.

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VALID_PROJECT_YAML_INSTANCE = """
metadata:
  name: wasm-module-template
  description: WASM guest module template
  version: 0.1.0
  license: CC-BY-NC-SA-4.0
  main_branch: wasm/main
  owner: Gabor Zoltan Sinko
  buildHash: deadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00d
compiler_settings:
  repo_type: module
  component_name: wasm-module
  meta_schemas_dir: ./
  meta_schema_file: md.meta.schema.yaml
  canonical_source_file: schemas/index.yaml
  source_dir: ./
  vault_key_name: cic-my-sign-key
abi:
  name: wasm-module-template
  version: "1.0.0"
  envelopeVersion: 1
  exports:
    - allocate
    - deallocate
    - Call
  operations:
    - init
    - process
    - get
    - notify
"""

INVALID_PROJECT_YAML_INSTANCE = """
metadata:
  name: wasm-module-template
  description: WASM guest module template
  main_branch: wasm/main
  owner: Gabor Zoltan Sinko
  buildHash: deadbeefcafef00d
compiler_settings:
  component_name: wasm-module
  meta_schemas_dir: ./
  meta_schema_file: md.meta.schema.yaml
  source_dir: ./
  vault_key_name: cic-my-sign-key
"""


class TestValidateFinalProjectYamlRealSchema:
    @pytest.fixture
    def real_schema_manager(
        self, mock_config, mock_git_service, mock_vault_service, mocker, tmp_path
    ):
        # Copy the real project.schema.yaml (and the abi.schema.yaml it
        # $ref's) into a scratch project root so the test exercises the
        # actual schemas shipped with the repository, without mutating them.
        for name in ("project.schema.yaml", "abi.schema.yaml"):
            (tmp_path / name).write_text((PROJECT_ROOT / name).read_text())

        logger = mocker.MagicMock(spec=logging.Logger)
        return ReleaseManager(
            config=mock_config,
            git_service=mock_git_service,
            vault_service=mock_vault_service,
            project_root=tmp_path,
            dry_run=False,
            logger=logger,
        )

    def test_real_schema_accepts_valid_project_yaml(
        self, real_schema_manager, tmp_path
    ):
        (tmp_path / "project.yaml").write_text(VALID_PROJECT_YAML_INSTANCE)

        # Must not raise: validates against the real project.schema.yaml
        # without the schema["spec"] KeyError, and buildHash is non-empty.
        real_schema_manager._validate_final_project_yaml()

    def test_real_schema_rejects_project_yaml_missing_required_field(
        self, real_schema_manager, tmp_path
    ):
        (tmp_path / "project.yaml").write_text(INVALID_PROJECT_YAML_INSTANCE)

        with pytest.raises(
            ValidationFailureError, match="Final project.yaml validation failed"
        ):
            real_schema_manager._validate_final_project_yaml()

    def test_real_schema_rejects_empty_build_hash(self, real_schema_manager, tmp_path):
        instance = yaml.safe_load(VALID_PROJECT_YAML_INSTANCE)
        instance["metadata"]["buildHash"] = ""
        (tmp_path / "project.yaml").write_text(yaml.dump(instance))

        with pytest.raises(
            ValidationFailureError, match="metadata.buildHash is required"
        ):
            real_schema_manager._validate_final_project_yaml()
