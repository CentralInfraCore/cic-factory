import logging
import sys
from pathlib import Path
from unittest.mock import ANY, MagicMock

import pytest
import yaml

# Add project root to sys.path to allow importing 'tools'
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools import finalize_release
from tools.releaselib.exceptions import VaultServiceError

# --- Fixtures ---


@pytest.fixture
def mock_args(mocker):
    """Fixture to mock argparse arguments with MagicMocks for paths."""
    args = MagicMock()

    args.filepath = MagicMock(spec=Path)
    args.filepath.exists.return_value = True
    args.filepath.__str__.return_value = "project.yaml"

    args.cic_cert_file = MagicMock(spec=Path)
    args.cic_cert_file.exists.return_value = True
    args.cic_cert_file.__str__.return_value = "ca.crt"

    args.cic_vault_key = "test-key"
    args.cic_cert_vault_path = None
    args.dry_run = False
    args.verbose = False
    args.debug = False

    mocker.patch("argparse.ArgumentParser.parse_args", return_value=args)
    return args


@pytest.fixture
def mock_env(mocker):
    """Fixture to mock environment variables."""
    mocker.patch(
        "os.getenv",
        side_effect=lambda var: {
            "VAULT_ADDR": "https://fake-vault.com",
            "VAULT_TOKEN": "fake-token",
        }.get(var),
    )


@pytest.fixture
def mock_vault(mocker):
    """Fixture to mock the VaultService."""
    mock_vault_instance = MagicMock()
    mock_vault_instance.sign.return_value = "vault:v1:signed-hash"
    mock_vault_instance.get_certificate.return_value = (
        "-----BEGIN CERT-----\nVAULT-CERT\n-----END CERT-----"
    )
    mocker.patch(
        "tools.finalize_release.VaultService", return_value=mock_vault_instance
    )
    return mock_vault_instance


@pytest.fixture
def mock_sys_exit(mocker):
    """Fixture to mock sys.exit to prevent test termination."""
    return mocker.patch("sys.exit")


# --- Test Classes ---


class TestHelperFunctions:
    """Tests for helper functions like logging and YAML handling."""

    @pytest.mark.parametrize(
        "verbose, debug, expected_level",
        [
            (False, False, logging.WARNING),
            (True, False, logging.INFO),
            (False, True, logging.DEBUG),
        ],
    )
    def test_setup_logging(self, verbose, debug, expected_level):
        """Tests that logging is configured correctly for different verbosity levels."""
        # Use a unique logger name to avoid conflicts
        logger = logging.getLogger(f"test_logger_{verbose}_{debug}")
        logger.handlers = []

        with pytest.MonkeyPatch.context() as m:
            m.setattr(finalize_release.logging, "getLogger", lambda name: logger)
            finalize_release.setup_logging(verbose=verbose, debug=debug)

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert logger.handlers[0].level == expected_level

    def test_colored_formatter(self):
        """Tests the custom colored formatter."""
        formatter = finalize_release.ColoredFormatter(finalize_release.LOG_FORMAT)

        record_info = logging.LogRecord(
            "test", logging.INFO, "test", 1, "Info message", None, None
        )
        assert "INFO: Info message" in formatter.format(record_info)
        assert "\033[0m" in formatter.format(record_info)

        record_success = logging.LogRecord(
            "test", logging.INFO, "test", 1, "✓ Success message", None, None
        )
        assert "✓ Success message" in formatter.format(record_success)
        assert "\033[92m" in formatter.format(record_success)

        record_error = logging.LogRecord(
            "test", logging.ERROR, "test", 1, "Error message", None, None
        )
        assert "Error message" in formatter.format(record_error)
        assert "\033[91m" in formatter.format(record_error)

    def test_load_yaml_io_error(self, mocker, caplog):
        """Tests the exception handling in load_yaml for IOError."""
        caplog.set_level(logging.CRITICAL)
        mocker.patch("builtins.open", side_effect=IOError("Permission denied"))
        with pytest.raises(IOError):
            finalize_release.load_yaml(Path("any.yaml"))
        assert "Error loading YAML file any.yaml: Permission denied" in caplog.text

    def test_load_yaml_yaml_error(self, mocker, caplog):
        """Tests the exception handling in load_yaml for YAMLError."""
        caplog.set_level(logging.CRITICAL)
        mocker.patch("builtins.open", mocker.mock_open(read_data=": invalid yaml"))
        with pytest.raises(yaml.YAMLError):
            finalize_release.load_yaml(Path("any.yaml"))
        assert "Error loading YAML file any.yaml" in caplog.text

    def test_write_yaml_io_error(self, mocker, caplog):
        """Tests the exception handling in write_yaml."""
        caplog.set_level(logging.CRITICAL)
        mocker.patch("builtins.open", side_effect=IOError("Disk full"))
        with pytest.raises(IOError):
            finalize_release.write_yaml(Path("any.yaml"), {})
        assert "Error writing YAML file any.yaml: Disk full" in caplog.text


class TestMainExecution:
    """Test suite for the main execution logic of the script."""

    @pytest.fixture(autouse=True)
    def setup_main_mocks(self, mocker):
        """Mock dependencies for the main function execution tests."""
        mocker.patch(
            "tools.finalize_release.setup_logging", return_value=logging.getLogger()
        )
        mocker.patch(
            "tools.finalize_release.load_yaml",
            return_value={
                "metadata": {"checksum": "dummy-hash", "buildHash": "dummy-hash"}
            },
        )
        self.mock_write_yaml = mocker.patch("tools.finalize_release.write_yaml")

    def test_main_success_with_cert_file(self, mock_args, mock_env, mock_vault, mocker):
        cert_content = "-----BEGIN CERT-----\nFILE-CERT\n-----END CERT-----"
        mock_open = mocker.patch(
            "builtins.open", mocker.mock_open(read_data=cert_content)
        )

        finalize_release.main()

        mock_open.assert_called_once_with(
            mock_args.cic_cert_file, "r", encoding="utf-8"
        )
        final_data = self.mock_write_yaml.call_args[0][1]
        assert final_data["metadata"]["cicSignedCA"]["certificate"] == cert_content
        assert final_data["metadata"]["cicSign"] == "vault:v1:signed-hash"
        self.mock_write_yaml.assert_called_once_with(mock_args.filepath, ANY)

    def test_main_success_with_vault_path(self, mock_args, mock_env, mock_vault):
        mock_args.cic_cert_file = None
        mock_args.cic_cert_vault_path = "kv/data/secrets/my-cert:cert_key"

        finalize_release.main()

        mock_vault.get_certificate.assert_called_once_with(
            "kv/data", "secrets/my-cert", "cert_key"
        )
        final_data = self.mock_write_yaml.call_args[0][1]
        assert (
            final_data["metadata"]["cicSignedCA"]["certificate"]
            == mock_vault.get_certificate.return_value
        )
        self.mock_write_yaml.assert_called_once_with(mock_args.filepath, ANY)

    def test_main_dry_run(
        self, mock_args, mock_env, mock_vault, capsys, caplog, mocker
    ):
        mock_args.dry_run = True
        mocker.patch("builtins.open", mocker.mock_open(read_data="cert-data"))
        caplog.set_level(logging.INFO)

        finalize_release.main()

        self.mock_write_yaml.assert_not_called()
        assert "--- DRY-RUN: Final YAML content ---" in caplog.text
        captured = capsys.readouterr()
        assert "buildHash: dummy-hash" in captured.out

    def test_error_filepath_not_found(self, mock_args, mock_env, mock_sys_exit, caplog):
        mock_args.filepath.exists.return_value = False

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: The specified file was not found"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_error_cert_file_not_found(
        self, mock_args, mock_env, mock_sys_exit, caplog
    ):
        mock_args.cic_cert_file.exists.return_value = False

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: The CIC certificate file was not found"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_error_checksum_mismatch(
        self, mock_args, mock_env, mock_sys_exit, caplog, mocker
    ):
        mocker.patch(
            "tools.finalize_release.load_yaml",
            return_value={
                "metadata": {"checksum": "dummy-hash", "buildHash": "different-hash"}
            },
        )

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: Validation failed: 'checksum' and 'buildHash' do not match!"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_error_no_metadata_block(
        self, mock_args, mock_env, mock_sys_exit, caplog, mocker
    ):
        mocker.patch(
            "tools.finalize_release.load_yaml", return_value={"other_data": "value"}
        )

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: The 'metadata' block was not found"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_error_vault_signing_fails(
        self, mock_args, mock_env, mock_vault, mock_sys_exit, caplog, mocker
    ):
        mocker.patch("builtins.open", mocker.mock_open(read_data="cert-data"))
        mock_vault.sign.side_effect = VaultServiceError("Vault signing failed")

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: Vault signing failed"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_error_vault_cert_fetch_fails(
        self, mock_args, mock_env, mock_vault, mock_sys_exit, caplog
    ):
        mock_args.cic_cert_file = None
        mock_args.cic_cert_vault_path = "kv/data/secrets/my-cert:cert_key"
        mock_vault.get_certificate.side_effect = VaultServiceError("Vault fetch failed")

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: Could not retrieve certificate from Vault: Vault fetch failed"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_error_invalid_vault_path_format(
        self, mock_args, mock_env, mock_vault, mock_sys_exit, caplog
    ):
        mock_args.cic_cert_file = None
        mock_args.cic_cert_vault_path = "invalid-path-format"

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: Could not retrieve certificate from Vault: Vault path must be in the format 'mount/path/to/secret:key'"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_error_missing_env_vars(self, mock_args, mock_sys_exit, caplog, mocker):
        mocker.patch(
            "os.getenv",
            side_effect=lambda var: {"VAULT_ADDR": "https://fake-vault.com"}.get(var),
        )

        finalize_release.main()

        assert (
            "[FAILURE] The finalization process failed: VAULT_ADDR and VAULT_TOKEN environment variables must be set"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)

    def test_unexpected_error_handling(
        self, mock_args, mock_env, mock_sys_exit, caplog, mocker
    ):
        mocker.patch(
            "tools.finalize_release.load_yaml",
            side_effect=Exception("Unexpected boom!"),
        )

        finalize_release.main()

        assert (
            "[UNEXPECTED ERROR] An unhandled exception occurred: Unexpected boom!"
            in caplog.text
        )
        mock_sys_exit.assert_called_once_with(1)
