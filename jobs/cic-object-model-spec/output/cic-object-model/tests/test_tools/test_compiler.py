import logging
import os
import sys
from unittest.mock import mock_open

import pytest

# Project root: /app
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Always put the project root at the beginning of sys.path
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from tools.compiler import (  # noqa: E402
    ColoredFormatter,
    load_project_config,
    main,
    setup_logging,
)
from tools.releaselib.exceptions import (  # noqa: E402
    ManualInterventionRequired,
    ReleaseError,
)


@pytest.fixture(autouse=True)
def mock_env(mocker):
    """Auto-mock environment and services for all tests in this module."""
    mocker.patch(
        "tools.compiler.load_project_config",
        return_value={"compiler_settings": {"some": "config"}},
    )
    mocker.patch(
        "tools.compiler.setup_logging", return_value=logging.getLogger("test_logger")
    )
    mocker.patch("tools.compiler.GitService")
    mocker.patch("tools.compiler.VaultService")
    mocker.patch("os.path.exists", return_value=False)


class TestMainCLI:
    def test_no_arguments(self, mocker):
        mocker.patch.object(sys, "argv", ["compiler.py"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2

    def test_validate_command_success(self, mocker):
        mocker.patch.object(sys, "argv", ["compiler.py", "validate"])
        mock_release_manager_class = mocker.patch("tools.compiler.ReleaseManager")
        mock_rm_instance = mock_release_manager_class.return_value

        main()

        mock_release_manager_class.assert_called_once()
        mock_rm_instance.run_validation.assert_called_once()
        mock_rm_instance.run_release_close.assert_not_called()  # Changed from run_release

    def test_release_command_requires_version(self, mocker):
        mocker.patch.object(sys, "argv", ["compiler.py", "release"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2

    def test_release_command_success(self, mocker):
        """Test the 'release' command success case."""
        mocker.patch.object(
            sys, "argv", ["compiler.py", "release", "--version", "1.2.3"]
        )
        mock_release_manager_class = mocker.patch("tools.compiler.ReleaseManager")
        mock_rm_instance = mock_release_manager_class.return_value

        main()

        mock_release_manager_class.assert_called_once()
        # The main method now only calls run_release_close, which orchestrates everything else.
        mock_rm_instance.run_release_close.assert_called_once_with(
            release_version="1.2.3"
        )  # Changed from run_release
        # We no longer check for internal calls like run_validation from this top-level test.
        mock_rm_instance.run_validation.assert_not_called()

    def test_release_command_with_vault_files(self, mocker):
        """Test 'release' command reads Vault token and CA from files."""
        mocker.patch.object(
            sys, "argv", ["compiler.py", "release", "--version", "1.2.3"]
        )
        mocker.patch("tools.compiler.ReleaseManager")
        mock_vault_service = mocker.patch("tools.compiler.VaultService")

        mocker.patch.dict(
            os.environ,
            {
                "VAULT_TOKEN": "",
                "VAULT_ADDR": "http://mock-vault:8200",
                "VAULT_CACERT": "",
            },
            clear=True,
        )

        def path_exists_side_effect(path):
            return path in [
                "/var/run/secrets/vault-token",
                "/var/run/secrets/vault-ca.crt",
            ]

        mocker.patch("os.path.exists", side_effect=path_exists_side_effect)
        mocker.patch("builtins.open", mock_open(read_data="file-token"))

        main()

        args, kwargs = mock_vault_service.call_args
        assert kwargs.get("vault_token") == "file-token"
        assert kwargs.get("vault_cacert") == "/var/run/secrets/vault-ca.crt"

    def test_main_handles_manual_intervention(self, mocker):
        """Test that main catches ManualInterventionRequired and exits with 0."""
        mocker.patch.object(
            sys, "argv", ["compiler.py", "release", "--version", "1.0.0"]
        )
        mock_release_manager_class = mocker.patch("tools.compiler.ReleaseManager")
        mock_rm_instance = mock_release_manager_class.return_value
        mock_rm_instance.run_release_close.side_effect = ManualInterventionRequired(
            "Do something"
        )  # Changed from run_release

        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    def test_main_handles_release_error(self, mocker):
        mocker.patch.object(sys, "argv", ["compiler.py", "validate"])
        mock_release_manager_class = mocker.patch("tools.compiler.ReleaseManager")
        mock_rm_instance = mock_release_manager_class.return_value
        mock_rm_instance.run_validation.side_effect = ReleaseError("Test error")

        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


class TestConfigLoader:
    @pytest.fixture(autouse=False)
    def mock_env(self, mocker):
        pass

    def test_load_project_config_io_error(self, mocker):
        mocker.patch("builtins.open", side_effect=IOError("File not found"))
        with pytest.raises(SystemExit) as excinfo:
            load_project_config()
        assert excinfo.value.code == 1

    def test_load_project_config_key_error(self, mocker):
        mocker.patch("builtins.open", mock_open(read_data="{}"))
        mocker.patch("yaml.safe_load", return_value={})
        with pytest.raises(SystemExit) as excinfo:
            load_project_config()
        assert excinfo.value.code == 1


class TestLogging:
    @pytest.fixture(autouse=True)
    def unpatch_logging(self, mocker):
        mocker.stopall()

    def test_setup_logging_levels(self):
        logger = logging.getLogger("tools.compiler")
        logger.handlers = []
        handler = setup_logging(verbose=True).handlers[0]
        assert handler.level == logging.INFO
        logger.handlers = []
        handler = setup_logging(debug=True).handlers[0]
        assert handler.level == logging.DEBUG
        logger.handlers = []
        handler = setup_logging().handlers[0]
        assert handler.level == logging.WARNING
        logger.handlers = []

    def test_colored_formatter(self):
        formatter = ColoredFormatter("%(message)s")

        dry_run_record = logging.LogRecord(
            "test", logging.INFO, "", 0, "DRY-RUN: test", None, None
        )
        assert "\033[96m" in formatter.format(dry_run_record)

        success_record = logging.LogRecord(
            "test", logging.INFO, "", 0, "✓ Success", None, None
        )
        assert "\033[92m" in formatter.format(success_record)

        error_record = logging.LogRecord(
            "test", logging.ERROR, "", 0, "Error message", None, None
        )
        assert "\033[91m" in formatter.format(error_record)

        info_record = logging.LogRecord(
            "test", logging.INFO, "", 0, "Info message", None, None
        )
        formatted_msg = formatter.format(info_record)
        assert "\033[0m" in formatted_msg
        assert "\033[96m" not in formatted_msg
        assert "\033[92m" not in formatted_msg
