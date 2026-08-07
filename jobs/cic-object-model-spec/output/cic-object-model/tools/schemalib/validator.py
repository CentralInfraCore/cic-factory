import logging
from pathlib import Path

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate

from ..releaselib.exceptions import ReleaseError
from .artifact import compute_spec_checksum
from .loader import load_and_resolve_schema


class ValidationFailureError(ReleaseError):
    """Raised when schema validation or validator integrity check fails."""

    pass


def verify_validator_integrity(validator_schema: dict) -> None:
    """
    Verifies the SHA-256 checksum of a validator schema's spec block
    against the expected value stored in its own metadata.

    This is a security control: a tampered validator could silently
    accept invalid schemas.

    Raises:
        ValidationFailureError: if the checksum is missing or does not match.
    """
    logger = logging.getLogger(__name__)
    expected = validator_schema.get("metadata", {}).get("checksum")
    if not expected:
        raise ValidationFailureError(
            "Validator schema is missing 'metadata.checksum'. "
            "Cannot verify integrity."
        )

    actual = compute_spec_checksum(validator_schema["spec"])

    if actual != expected:
        name = validator_schema.get("metadata", {}).get("name", "unknown")
        raise ValidationFailureError(
            f"Validator schema '{name}' integrity check FAILED. "
            f"Expected checksum: {expected[:12]}... "
            f"Actual: {actual[:12]}... "
            "The schema may have been tampered with."
        )

    logger.debug(
        f"✓ Validator integrity OK: {validator_schema.get('metadata', {}).get('name')}"
    )


def get_validator_schema(
    validator_name: str,
    validator_version: str,
    source_schema: dict,
    dependencies_dir: Path,
) -> dict:
    """
    Loads a validator schema from the dependencies/ directory.
    Expected file name pattern: <name>-<version>.yaml

    Special case: if the validator_name matches the source schema's own name,
    self-validation (bootstrap) is detected and the source schema itself
    is returned as the validator.

    Before returning, calls verify_validator_integrity() to ensure
    the schema has not been tampered with. (Skipped for self-validation.)

    Args:
        validator_name: name field from source_schema['metadata']['validatedBy']['name']
        validator_version: version field from validatedBy
        source_schema: the already-loaded source schema dict
        dependencies_dir: path to the dependencies/ directory

    Raises:
        ConfigurationError: if the validator file is not found.
        ValidationFailureError: if the integrity check fails.
    """
    source_name = source_schema.get("metadata", {}).get("name")
    if validator_name == source_name:
        logging.getLogger(__name__).info(
            f"Self-validation (bootstrap) detected for '{source_name}'. "
            "Using source schema as its own validator."
        )
        return source_schema

    validator_filename = f"{validator_name}-{validator_version}.yaml"
    validator_path = dependencies_dir / validator_filename

    logging.getLogger(__name__).info(f"Loading external validator: {validator_path}")

    validator_schema = load_and_resolve_schema(validator_path)

    verify_validator_integrity(validator_schema)

    return validator_schema


def run_validation(instance: dict, validator_schema: dict) -> None:
    """
    Runs jsonschema.validate() against instance using validator_schema['spec'].

    Raises:
        ValidationFailureError: on validation failure.
    """
    logger = logging.getLogger(__name__)
    validator_name = validator_schema.get("metadata", {}).get("name", "unknown")
    validator_version = validator_schema.get("metadata", {}).get("version", "unknown")

    try:
        validate(instance=instance, schema=validator_schema["spec"])
        logger.info(f"✓ Valid against {validator_name}@{validator_version}")
    except JsonSchemaValidationError as e:
        raise ValidationFailureError(
            f"Schema validation FAILED against "
            f"{validator_name}@{validator_version}: {e.message}"
        ) from e
    except KeyError as e:
        raise ValidationFailureError(
            f"Validator schema '{validator_name}' is missing the 'spec' block: {e}"
        ) from e
