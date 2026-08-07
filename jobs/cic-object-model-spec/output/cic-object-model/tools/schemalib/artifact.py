import base64
import hashlib
import json
import logging
from typing import Optional

from OpenSSL import crypto
from OpenSSL.SSL import Error as OpenSSLError


def to_canonical_json(data: dict) -> bytes:
    """Converts a Python object to a canonical (sorted, no whitespace) JSON bytes."""
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_spec_checksum(spec: dict) -> str:
    """
    Computes a canonical SHA-256 hex digest of the spec block.
    Uses json.dumps(sort_keys=True) for determinism.
    Returns: hex string (64 chars)
    """
    return hashlib.sha256(to_canonical_json(spec)).hexdigest()


def get_sha256_hex(data_bytes: bytes) -> str:
    """Calculates the SHA256 hash and returns it as a hex digest."""
    return hashlib.sha256(data_bytes).hexdigest()


def get_sha256_b64(data_bytes: bytes) -> str:
    """Calculates the SHA256 hash and returns it as a base64 encoded string."""
    return base64.b64encode(hashlib.sha256(data_bytes).digest()).decode("utf-8")


def parse_certificate_info(pem_cert_data: str) -> tuple[str, str]:
    """
    Parses a PEM-encoded certificate using pyOpenSSL.
    Extracts Common Name and email (from SubjectAltName or emailAddress field).

    Returns:
        (name, email) — falls back to ("Unknown", "unknown@example.com") on error.
    """
    logger = logging.getLogger(__name__)
    try:
        cert = crypto.load_certificate(
            crypto.FILETYPE_PEM, pem_cert_data.encode("utf-8")
        )
        subject = cert.get_subject()
        name = subject.CN
        email: Optional[str] = None

        for i in range(cert.get_extension_count()):
            ext = cert.get_extension(i)
            if ext.get_short_name() == b"subjectAltName":
                for alt_name in str(ext).split(", "):
                    if alt_name.startswith("email:"):
                        email = alt_name[len("email:") :]
                        break

        if not email:
            email = subject.emailAddress

        return name or "Unknown", email or "unknown@example.com"
    except (OpenSSLError, Exception) as e:
        logger.warning(f"Could not parse certificate with pyOpenSSL: {e}")
        return "Unknown", "unknown@example.com"


def build_signing_payload(
    name: str,
    version: str,
    checksum: str,
    build_timestamp: str,
) -> str:
    """
    Constructs the base64-encoded SHA-256 digest of the canonical signing
    metadata dict. This is the input to VaultService.sign() with prehashed=True.

    Returns:
        base64 string (suitable for Vault's transit sign endpoint)
    """
    metadata_for_signing = {
        "name": name,
        "version": version,
        "checksum": checksum,
        "build_timestamp": build_timestamp,
    }
    digest_bytes = hashlib.sha256(to_canonical_json(metadata_for_signing)).digest()
    return base64.b64encode(digest_bytes).decode("utf-8")


def generate_signed_artifact(
    spec: dict,
    name: str,
    version: str,
    checksum: str,
    build_timestamp: str,
    developer_cert: str,
    issuer_cert: str,
    signature: str,
    validator_name: Optional[str] = None,
    validator_version: Optional[str] = None,
    validator_checksum: Optional[str] = None,
) -> dict:
    """
    Assembles the complete release artifact dict to be written to
    release/<name>-<version>.yaml (schema repos) or equivalent.

    The returned structure contains:
        metadata: name, version, checksum, sign, build_timestamp,
                  createdBy, validatedBy (if provided),
                  buildHash: ""      (placeholder, filled by build step)
                  cicSign: ""        (placeholder, filled by relay)
                  cicSignedCA.certificate: ""  (placeholder)
        spec: <the resolved spec dict>
    """
    cert_name, cert_email = parse_certificate_info(developer_cert)

    metadata: dict = {
        "name": name,
        "version": version,
        "checksum": checksum,
        "sign": signature,
        "build_timestamp": build_timestamp,
        "createdBy": {
            "name": cert_name,
            "email": cert_email,
            "certificate": developer_cert,
            "issuer_certificate": issuer_cert,
        },
        "buildHash": "",
        "cicSign": "",
        "cicSignedCA": {"certificate": ""},
    }

    if validator_name and validator_version:
        metadata["validatedBy"] = {
            "name": validator_name,
            "version": validator_version,
        }
        if validator_checksum:
            metadata["validatedBy"]["checksum"] = validator_checksum

    return {"metadata": metadata, "spec": spec}
