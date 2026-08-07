import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.request import url2pathname

import yaml
from jsonref import JsonRef

from ..releaselib.exceptions import ConfigurationError, ReleaseError


def convert_to_json_serializable(obj: Any) -> Any:
    """
    Recursively converts a Python object graph to one that is fully
    JSON-serialisable. Handles JsonRef proxies (by forcing resolution),
    datetime objects (to ISO-8601 strings), and nested dicts/lists.
    """
    if isinstance(obj, JsonRef):
        if hasattr(obj, "keys"):
            obj = dict(obj)
        elif isinstance(obj, list):
            obj = list(obj)
        else:
            return obj

    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(elem) for elem in obj]
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return obj


def load_and_resolve_schema(path: Path) -> dict:
    """
    Loads a YAML file, resolves all $ref references (including cross-file
    references using the file's directory as base URI), then performs a
    JSON round-trip via convert_to_json_serializable() to guarantee that
    the returned object contains only plain Python types.

    Raises:
        ConfigurationError: if the file is missing or YAML is malformed.
    Returns:
        dict: Fully resolved, JSON-serialisable document.
    """
    try:

        def yaml_loader(uri):
            local_path = url2pathname(urlparse(uri).path)
            with open(local_path, "r") as f_loader:
                content = f_loader.read()
                if not content.strip():
                    return {}
                return yaml.safe_load(content)

        with open(path, "r") as f:
            base_uri = f"file://{os.path.dirname(os.path.abspath(path))}/"
            unresolved_data = yaml.safe_load(f)

            resolved_jsonref = JsonRef.replace_refs(
                unresolved_data, base_uri=base_uri, loader=yaml_loader
            )

            plain_data = convert_to_json_serializable(resolved_jsonref)

            class _DatetimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime.datetime):
                        return obj.isoformat()
                    return super().default(obj)

            return json.loads(json.dumps(plain_data, cls=_DatetimeEncoder))

    except FileNotFoundError as e:
        raise ConfigurationError(f"File not found: {path}") from e
    except yaml.YAMLError as e:
        raise ConfigurationError(f"YAML parsing error in {path}: {e}") from e
    except Exception as e:
        raise ConfigurationError(
            f"Unexpected error loading schema from {path}: {e}"
        ) from e


def load_yaml(path: Path) -> Optional[dict]:
    """
    Loads a YAML file without $ref resolution. Returns None for empty files.

    Raises:
        ConfigurationError: on missing file or parse error.
    """
    try:
        with open(path, "r") as f:
            content = f.read()
            if not content.strip():
                return None
            return yaml.safe_load(content)
    except FileNotFoundError as e:
        raise ConfigurationError(f"Configuration file not found at: {path}") from e
    except yaml.YAMLError as e:
        raise ConfigurationError(f"YAML syntax error in {path}: {e}") from e


def write_yaml(path: Path, data: dict) -> None:
    """
    Atomically writes data to a YAML file using a temp-file + os.replace() pattern.

    Raises:
        ReleaseError: on I/O failure.
    """
    tmp_name = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=path.parent, encoding="utf-8"
        ) as tmp_file:
            tmp_name = tmp_file.name
            yaml.dump(data, tmp_file, sort_keys=False, indent=2, allow_unicode=True)
        os.replace(tmp_name, path)
    except (IOError, OSError) as e:
        raise ReleaseError(f"Failed to write YAML file to {path}: {e}") from e
    finally:
        if tmp_name and Path(tmp_name).exists():
            try:
                Path(tmp_name).unlink()
            except Exception:  # nosec B110 - best-effort cleanup of temp file
                pass
