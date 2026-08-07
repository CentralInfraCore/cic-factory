import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.infra import (
    ConfigurationError,
    ReleaseError,
    ReleaseManager,
    ValidationFailureError,
    load_and_resolve_schema,
    load_yaml,
    write_yaml,
)
from tools.releaselib.exceptions import VaultServiceError
from tools.releaselib.git_service import GitService
from tools.releaselib.vault_service import VaultService

# --- Fixtures ---


@pytest.fixture
def mock_git_service(mocker):
    """Mock GitService."""
    service = mocker.MagicMock(spec=GitService)
    service.get_current_branch.return_value = "main"
    service.is_dirty.return_value = False
    service.assert_clean_index.return_value = None
    return service


@pytest.fixture
def mock_vault_service(mocker):
    """Mock VaultService."""
    service = mocker.MagicMock(spec=VaultService)
    return service


@pytest.fixture
def full_mock_config():
    """Provides a full, valid config dictionary for complex tests."""
    return {
        "component_name": "base",
        "main_branch": "main",
        "vault_key_name": "test-key",
        "vault_cert_mount": "kv",
        "vault_cert_secret_name": "user-cert",
        "vault_cert_secret_key": "cert-key",
        "cic_root_ca_secret_name": "cic-root",
        "meta_schema_file": "project.schema.yaml",
        "canonical_source_file": "sources/index.yaml",
    }


@pytest.fixture
def manager(mock_git_service, mock_vault_service, mocker):
    """Creates a base ReleaseManager instance."""
    logger = mocker.MagicMock(spec=logging.Logger)
    # Use a minimal config by default
    config = {
        "component_name": "base",
        "main_branch": "main",
        "meta_schema_file": "project.schema.yaml",
        "canonical_source_file": "sources/index.yaml",
    }
    return ReleaseManager(
        config=config,
        git_service=mock_git_service,
        vault_service=mock_vault_service,
        project_root=Path("/fake/project"),
        dry_run=False,
        logger=logger,
    )


# --- Coverage-focused Tests ---


class TestInfraCoverage:
    """This class contains tests specifically aimed at increasing code coverage."""

    def test_load_yaml_empty_content(self, mocker):
        """Covers the case where a YAML file contains only whitespace."""
        mocker.patch("builtins.open", mocker.mock_open(read_data=" \n\t "))
        assert load_yaml(Path("empty.yaml")) is None

    def test_write_yaml_cleanup_on_error(self, mocker):
        """Covers the finally block in write_yaml to ensure cleanup."""
        mock_tmp_file = MagicMock()
        mock_tmp_file.name = "/fake/dir/temp123"
        mocker.patch(
            "tools.schemalib.loader.tempfile.NamedTemporaryFile",
            return_value=mock_tmp_file,
        )
        mocker.patch(
            "tools.schemalib.loader.os.replace",
            side_effect=OSError("permission denied"),
        )

        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mocker.patch("tools.schemalib.loader.Path", return_value=mock_path_instance)

        with pytest.raises(ReleaseError):
            write_yaml(Path("any.yaml"), {})

        mock_path_instance.unlink.assert_called_once()

    def test_release_manager_init_no_logger(
        self, full_mock_config, mock_git_service, mock_vault_service
    ):
        """Covers the else branch in ReleaseManager.__init__ for the logger."""
        manager = ReleaseManager(
            config=full_mock_config,
            git_service=mock_git_service,
            vault_service=mock_vault_service,
        )
        assert isinstance(manager.logger, logging.Logger)

    def test_finalization_dry_run(self, manager, mocker):
        """Covers the dry_run=True path in _execute_finalization_phase."""
        manager.dry_run = True
        mocker.patch("tools.infra.ReleaseManager._validate_final_project_yaml")
        mocker.patch("tools.infra.ReleaseManager._resign_with_build_hash")

        manager._execute_finalization_phase(
            "1.0.0", "base", "main", "base/releases/v1.0.0"
        )

        # Assert that no git commands that modify state are run
        assert manager.git_service.add.call_count == 0
        assert manager.git_service.run.call_count == 0
        assert manager.git_service.checkout.call_count == 0
        assert manager.git_service.merge.call_count == 0
        assert manager.git_service.delete_branch.call_count == 0
        manager.logger.info.assert_any_call(
            "✓ Release v1.0.0 successfully finalized and merged into 'main'."
        )

    def test_run_release_close_no_vault_service(self, manager):
        """Covers the VaultService not initialized error."""
        manager.vault_service = None
        with pytest.raises(VaultServiceError, match="VaultService is not initialized"):
            manager.run_release_close("1.0.0")

    def test_load_and_resolve_schema_yaml_error(self, mocker):
        mocker.patch("builtins.open", mocker.mock_open(read_data=": invalid yaml"))
        with pytest.raises(ConfigurationError, match="YAML parsing error"):
            load_and_resolve_schema("invalid.yaml")

    def test_validate_final_yaml_empty_schema(self, manager, mocker):
        mocker.patch("tools.infra.load_and_resolve_schema", return_value=None)
        with pytest.raises(
            ValidationFailureError, match="Project schema file.*is empty"
        ):
            manager._validate_final_project_yaml()

    def test_validate_final_yaml_empty_instance(self, manager, mocker):
        mocker.patch("tools.infra.load_and_resolve_schema", return_value={"spec": {}})
        mocker.patch("tools.infra.load_yaml", return_value=None)
        with pytest.raises(ValidationFailureError, match="Project YAML file.*is empty"):
            manager._validate_final_project_yaml()

    def test_validate_final_yaml_generic_exception(self, manager, mocker):
        mocker.patch(
            "tools.infra.load_and_resolve_schema", side_effect=Exception("Boom!")
        )
        with pytest.raises(ReleaseError, match="An unexpected error occurred"):
            manager._validate_final_project_yaml()

    def test_developer_prep_with_main_component(
        self, manager, full_mock_config, mocker
    ):
        manager.config = full_mock_config
        manager.config["component_name"] = "main"
        mocker.patch(
            "tools.infra.load_and_resolve_schema",
            return_value={"spec": {}, "metadata": {}},
        )
        mocker.patch("tools.infra.load_yaml", return_value={})
        mocker.patch("tools.infra.write_yaml")
        mocker.patch(
            "tools.infra._parse_certificate_info",
            return_value=("Test", "test@test.com"),
        )

        manager._execute_developer_preparation_phase("1.0.0", "main", "main")

        manager.git_service.checkout.assert_called_once_with(
            "releases/v1.0.0", create_new=True
        )

    def test_developer_prep_cleanup_fails(self, manager, mocker):
        mocker.patch(
            "tools.infra.load_and_resolve_schema",
            side_effect=ValueError("Initial error"),
        )
        manager.git_service.delete_branch.side_effect = Exception("Cleanup failed")

        with pytest.raises(ReleaseError, match="Initial error"):
            manager._execute_developer_preparation_phase("1.0.0", "base", "main")

        manager.logger.critical.assert_any_call(
            "Failed to clean up release branch: Cleanup failed", exc_info=True
        )

    def test_finalization_with_dirty_repo(self, manager, mocker):
        manager.git_service.get_current_branch.return_value = "base/releases/v1.0.0"
        manager.git_service.is_dirty.return_value = True
        mocker.patch("tools.infra.ReleaseManager._validate_final_project_yaml")
        mocker.patch("tools.infra.ReleaseManager._resign_with_build_hash")

        manager._execute_finalization_phase(
            "1.0.0", "base", "base/releases/v1.0.0", "base/releases/v1.0.0"
        )

        manager.git_service.run.assert_any_call(
            ["git", "commit", "-m", "release: Finalize base v1.0.0 build artifacts"]
        )
        manager.logger.info.assert_any_call(
            "Committing pending changes to project.yaml (from build process)..."
        )

    def test_run_validation_value_error(self, manager, mocker):
        mocker.patch(
            "tools.infra.load_and_resolve_schema",
            side_effect=ValueError("Some value error"),
        )
        with pytest.raises(ReleaseError, match="Schema validation failed"):
            manager.run_validation()
        manager.logger.critical.assert_any_call("VALIDATION FAILED: Some value error")

    def test_run_validation_generic_error(self, manager, mocker):
        mocker.patch(
            "tools.infra.load_and_resolve_schema", side_effect=Exception("Generic boom")
        )
        with pytest.raises(
            ReleaseError, match="An unexpected error occurred during validation"
        ):
            manager.run_validation()
        manager.logger.critical.assert_any_call(
            "UNEXPECTED ERROR during validation: Generic boom"
        )
