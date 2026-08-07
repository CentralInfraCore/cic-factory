import base64
import os

# Add project root to sys.path
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tools.releaselib.vault_service import VaultService, VaultServiceError

VALID_DIGEST_B64 = base64.b64encode(b" " * 32).decode("utf-8")


@pytest.fixture
def vault_service():
    """Fixture for a live VaultService instance."""
    return VaultService(vault_addr="http://fake-vault:8200", vault_token="test-token")


@pytest.fixture
def dry_run_vault_service():
    """Fixture for a dry-run VaultService instance."""
    return VaultService(
        vault_addr="http://fake-vault:8200", vault_token="test-token", dry_run=True
    )


def test_init_live_run_missing_credentials():
    """Test that live run initialization fails without credentials."""
    with pytest.raises(
        VaultServiceError, match="Vault address and token must be provided"
    ):
        VaultService(vault_addr=None, vault_token=None)


@patch("os.path.exists", return_value=False)
def test_init_live_run_cacert_not_found(mock_exists):
    """Test that live run initialization fails if CA cert is not found."""
    with pytest.raises(
        VaultServiceError, match="Provided Vault CA certificate file not found"
    ):
        VaultService(
            vault_addr="http://fake-vault:8200",
            vault_token="test-token",
            vault_cacert="/fake/ca.crt",
        )


@patch("os.path.exists", return_value=True)
def test_init_live_run_with_cacert(mock_exists):
    """Test successful live run initialization with a CA cert."""
    service = VaultService(
        vault_addr="http://fake-vault:8200",
        vault_token="test-token",
        vault_cacert="/fake/ca.crt",
    )
    assert service.verify_tls == "/fake/ca.crt"


def test_init_dry_run_no_credentials():
    """Test that dry run initialization succeeds without credentials."""
    try:
        VaultService(vault_addr=None, vault_token=None, dry_run=True)
    except VaultServiceError:
        pytest.fail(
            "Dry-run VaultService initialization should not require credentials."
        )


def test_sign_dry_run(dry_run_vault_service):
    """Test that sign in dry-run mode returns a placeholder."""
    signature = dry_run_vault_service.sign(VALID_DIGEST_B64, "my-key")
    assert signature == "vault:v1:dry-run-placeholder-signature"


def test_sign_invalid_base64(vault_service):
    """Test that sign fails with invalid base64."""
    with pytest.raises(VaultServiceError, match="Invalid Base64 digest format"):
        vault_service.sign("not-base64", "my-key")


@patch("requests.post")
def test_sign_success(mock_post, vault_service):
    """Test a successful signing operation."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"signature": "vault:v1:signed-hash"}}
    mock_post.return_value = mock_response

    signature = vault_service.sign(VALID_DIGEST_B64, "my-key")
    assert signature == "vault:v1:signed-hash"
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args.kwargs["json"]["input"] == VALID_DIGEST_B64


@patch("requests.post")
def test_sign_request_exception(mock_post, vault_service):
    """Test that a requests exception is wrapped in VaultServiceError."""
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")
    with pytest.raises(
        VaultServiceError, match="Vault signing request failed: Connection error"
    ):
        vault_service.sign(VALID_DIGEST_B64, "my-key")


@patch("requests.post")
def test_sign_http_error(mock_post, vault_service):
    """Test that an HTTP error from raise_for_status is handled."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "403 Forbidden"
    )
    mock_post.return_value = mock_response
    with pytest.raises(
        VaultServiceError, match="Vault signing request failed: 403 Forbidden"
    ):
        vault_service.sign(VALID_DIGEST_B64, "my-key")


@patch("requests.post")
def test_sign_invalid_json_response(mock_post, vault_service):
    """Test handling of a non-JSON response from Vault."""
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("No JSON object could be decoded")
    mock_response.text = "This is not JSON"
    mock_post.return_value = mock_response
    with pytest.raises(VaultServiceError, match="Invalid JSON in Vault response"):
        vault_service.sign(VALID_DIGEST_B64, "my-key")


@patch("requests.post")
def test_sign_missing_signature_in_response(mock_post, vault_service):
    """Test handling of a valid JSON response that is missing the signature."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"other_field": "value"}}
    mock_post.return_value = mock_response
    with pytest.raises(
        VaultServiceError, match="Invalid or missing signature in Vault response"
    ):
        vault_service.sign(VALID_DIGEST_B64, "my-key")


@patch("requests.post")
def test_sign_malformed_signature_in_response(mock_post, vault_service):
    """Test handling of a malformed signature string."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"signature": "not-a-vault-signature"}}
    mock_post.return_value = mock_response
    with pytest.raises(
        VaultServiceError, match="Invalid or missing signature in Vault response"
    ):
        vault_service.sign(VALID_DIGEST_B64, "my-key")


@patch("requests.post")
def test_sign_digest_wrong_length(mock_post, vault_service, caplog):
    """Test that a warning is logged for a digest of unexpected length."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"signature": "vault:v1:signed-hash"}}
    mock_post.return_value = mock_response

    short_digest = base64.b64encode(b"short").decode("utf-8")
    vault_service.sign(short_digest, "my-key")

    assert "Digest length is not 32 bytes" in caplog.text


def test_get_certificate_dry_run(dry_run_vault_service):
    """Test that get_certificate in dry-run mode returns a placeholder."""
    certificate = dry_run_vault_service.get_certificate("kv/data", "my-secret", "cert")
    assert (
        certificate
        == "-----BEGIN CERTIFICATE-----\nDRY-RUN-PLACEHOLDER\n-----END CERTIFICATE-----"
    )


@patch("requests.get")
def test_get_certificate_success(mock_get, vault_service):
    """Test a successful certificate retrieval operation."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"data": {"cert": "---BEGIN CERT---\nFAKE_CERT\n---END CERT---"}}
    }
    mock_get.return_value = mock_response

    certificate = vault_service.get_certificate("kv/data", "my-secret", "cert")
    assert certificate == "---BEGIN CERT---\nFAKE_CERT\n---END CERT---"
    mock_get.assert_called_once_with(
        "http://fake-vault:8200/v1/kv/data/data/my-secret",  # Corrected URL
        headers={"X-Vault-Token": "test-token"},
        verify=True,
        timeout=10,
    )


@patch("requests.get")
def test_get_certificate_request_exception(mock_get, vault_service):
    """Test that a requests exception during certificate retrieval is wrapped."""
    mock_get.side_effect = requests.exceptions.RequestException("Connection error")
    with pytest.raises(
        VaultServiceError, match="Vault KV request failed: Connection error"
    ):
        vault_service.get_certificate("kv/data", "my-secret", "cert")


@patch("requests.get")
def test_get_certificate_http_error(mock_get, vault_service):
    """Test that an HTTP error from raise_for_status during certificate retrieval is handled."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )
    mock_get.return_value = mock_response
    with pytest.raises(
        VaultServiceError, match="Vault KV request failed: 404 Not Found"
    ):
        vault_service.get_certificate("kv/data", "my-secret", "cert")


@patch("requests.get")
def test_get_certificate_invalid_json_response(mock_get, vault_service):
    """Test handling of a non-JSON response during certificate retrieval."""
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("No JSON object could be decoded")
    mock_response.text = "This is not JSON"
    mock_get.return_value = mock_response
    with pytest.raises(VaultServiceError, match="Invalid JSON in Vault KV response"):
        vault_service.get_certificate("kv/data", "my-secret", "cert")


@patch("requests.get")
def test_get_certificate_missing_secret_key_in_response(mock_get, vault_service):
    """Test handling of a valid JSON response missing the secret key."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"data": {"other_key": "some_value"}}
    }  # 'cert' is missing
    mock_get.return_value = mock_response
    with pytest.raises(
        VaultServiceError,
        match="Secret key 'cert' not found or is not a string in Vault response",
    ):
        vault_service.get_certificate("kv/data", "my-secret", "cert")


@patch("requests.get")
def test_get_certificate_secret_key_not_string_in_response(mock_get, vault_service):
    """Test handling of a valid JSON response where the secret key's value is not a string."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"data": {"cert": 123}}
    }  # 'cert' is an int, not a string
    mock_get.return_value = mock_response
    with pytest.raises(
        VaultServiceError,
        match="Secret key 'cert' not found or is not a string in Vault response",
    ):
        vault_service.get_certificate("kv/data", "my-secret", "cert")


@patch("requests.post")
def test_sign_signature_not_string_in_response(mock_post, vault_service):
    """Test handling of a valid JSON response where the signature is not a string."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"signature": 123}}  # Not a string
    mock_post.return_value = mock_response
    with pytest.raises(
        VaultServiceError, match="Invalid or missing signature in Vault response"
    ):
        vault_service.sign(VALID_DIGEST_B64, "my-key")
