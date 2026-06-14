# wasm-infra-migration-impl — `tools/infra.py` migráció végrehajtása (Opció 1, 3-4. lépés) — riport

## Induló állapot

- `base-repo`: `wasm/main` @ `b7da285` (megegyezik a tervvel) — branch:
  `wasm/f/infra-migration`, pusholva.
- `CIC-Schemas`: `schemas/main` @ `2ec57c0` (klónozva referenciaként, **nem
  módosítva**).
- Baseline teszt-futás (lokális venv, `/tmp/wasm-infra-venv`, Python 3.12.3):
  `python3 -m pytest tests/test_tools/ -q --no-cov` → **112 passed**
  (a teljes `tests/test_tools/` szuit — a plan-riport 31-es száma csak
  `test_infra.py`+`test_infra_coverage.py`-ra vonatkozott; a 112-es a teljes
  jelenlegi baseline, ezt tartottam zölden mindvégig).

---

## Claim-evidence tábla (1-12. lépés)

| # | Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|---|
| 1 | **ADOPT**: `infra.py` import-blokk bővítve — `from .schemalib.artifact import build_signing_payload, compute_spec_checksum, parse_certificate_info, to_canonical_json`, `from .schemalib.loader import load_and_resolve_schema, load_yaml, write_yaml`, `from .schemalib.validator import ValidationFailureError`, `_parse_certificate_info = parse_certificate_info` back-compat alias. `requests`/`yaml`/`OpenPSSL`/`JsonRef`/`os`/`json`/`tempfile` importok ellenőrizve: a PRESERVE-elt `_validate_final_project_yaml`/`_resign_with_build_hash` nem hivatkozik rájuk közvetlenül (`grep` 0 találat) → törölve | done | `tools/infra.py:1-29` (új import-blokk); `grep -n "JsonRef\|crypto\|OpenSSLError\|\bos\.\|\bjson\.\|tempfile\." tools/infra.py` → **0 találat** a maradék kódban | `git diff tools/infra.py` (lásd lent), grep-kimenet | alacsony |
| 2 | **Törlés**: `infra.py:27-70` (dup. `ValidationFailureError`, `to_canonical_json`, `get_sha256_hex`, `_parse_certificate_info`) | done | `git diff tools/infra.py` — a teljes 97 soros dup.-blokk (`ValidationFailureError` class + 4 modul-szintű def) törölve | diff (lent) | alacsony |
| 3 | **Törlés**: `infra.py:73-123` (dup. `load_and_resolve_schema`, `load_yaml`, `write_yaml`) | done | ugyanaz a diff-hunk, lásd 2. sor | diff (lent) | alacsony |
| 4 | **Re-grep**: az 1-3. lépés után a kulcsmetódusok új sorszámai (`infra.py`, jelen állapot) | done | `grep -n "_resign_with_build_hash\|_execute_finalization_phase\|_validate_final_project_yaml\|_execute_developer_preparation_phase\|^class\|^def " tools/infra.py` → `class ReleaseManager:32`, `_validate_final_project_yaml:73`, `_execute_developer_preparation_phase:116`, `_resign_with_build_hash:254`, `_execute_finalization_phase:289`, hívás `_resign_with_build_hash` `:308`. A terv `~261-294`/`~315` becsléséhez képest a tényleges eltolódás **−91 sor → `_resign_with_build_hash` 254-287, hívás 308** (kicsit kisebb eltolódás, mert az 1. lépés import-blokkja +14 sort hozzáadott a −111-hez képest) | `grep -rn ...` futtatott kimenet (lásd a session-jegyzeteket) | alacsony — csak jegyzet, nem kódváltozás |
| 5 | **ADOPT**: `_execute_developer_preparation_phase` (most `infra.py:116-249`) — `compute_spec_checksum(source_data["spec"])` + `build_signing_payload(name=schema_name, version=..., checksum=..., build_timestamp=...)` + kétlépéses `createdBy` build-up (`name`/`email`: `None` → felülírás `_parse_certificate_info`-val, CIC-Schemas `infra.py:170-192` minta). `buildHash`/`cicSign`/`cicSignedCA` PRESERVE | done | `git diff tools/infra.py` (lent, "Assembling the developer-stage project.yaml metadata..." blokk) | `pytest tests/test_tools/ -q --no-cov` → 112 passed (lásd lent) | alacsony — futtatott teszt (`test_developer_preparation_phase_success`, `test_developer_prep_with_main_component`, `test_developer_prep_with_non_main_component`) mind PASS, a `_parse_certificate_info` patch-pont (CIC-Schemas mintában is `_parse_certificate_info`/`parse_certificate_info` néven hívva) érvényes maradt |
| 6 | **PRESERVE**: `_resign_with_build_hash` (`infra.py:254-287`) — törzs és hívási hely (`_execute_finalization_phase:289`, hívás `:308`) nem mozdult. `to_canonical_json` forrása már az 1. lépés óta `schemalib.artifact` — **nincs további edit szükséges** a metódus testében; `hashlib.sha256(...).digest()` + `base64.b64encode` marad (nem `get_sha256_hex`-alapú, az hex stringet adna, itt b64(raw digest) kell) | done — **eltérés a tervtől, dokumentálva** | `grep -n "_resign_with_build_hash\|to_canonical_json\|hashlib\|base64" tools/infra.py` → `to_canonical_json` egyetlen maradék hívása (`infra.py:271`) az 1. lépésben importált `schemalib.artifact.to_canonical_json`-ra mutat; `base64`/`hashlib` importok megtartva (csak itt használtak) | `pytest` 112 passed | alacsony — a terv 4. tétele "csak import-forrás cserét" írt elő, ez az 1. lépés automatikus következménye, nincs külön módosítandó kód |
| 7 | **PRESERVE** (sorhivatkozás frissítve): `finalize_release.py:21` `tools/infra.py:352-385` → `tools/infra.py:254-287` (a 4. lépés re-grep eredménye szerint) | done | `git diff tools/finalize_release.py` (lent) | `grep -n "tools/infra.py:254-287" tools/finalize_release.py` → 1 találat | alacsony — dokumentációs |
| 8 | **Patch-pont ellenőrzés** `test_infra_coverage.py`/`test_infra.py`: `tools.infra.load_and_resolve_schema/load_yaml/write_yaml/_parse_certificate_info`, `ReleaseManager._resign_with_build_hash`/`_validate_final_project_yaml` — **érvényesek maradtak** (a nevek importtal elérhetők `tools.infra` névtérben). **2 teszt módosítva** (eltérés a "nincs teendő" feltételezéstől): `test_parse_certificate_info_with_alt_name`/`_fallback_email` `tools.infra.crypto.load_certificate` → `tools.schemalib.artifact.crypto.load_certificate` (a `crypto` import elköltözött); `test_write_yaml_cleanup_on_error` `tools.infra.{tempfile,os,Path}` → `tools.schemalib.loader.{tempfile,os,Path}` (`write_yaml` törzse most a `schemalib.loader` névtérben fut, a `Path`-mock csak ott hat) | done — **2 teszt-igazítás dokumentálva** | `git diff tests/test_tools/test_infra.py tests/test_tools/test_infra_coverage.py` (lent) | `pytest` előtte: 3 FAIL (`test_parse_certificate_info_with_alt_name`, `test_parse_certificate_info_fallback_email`, `test_write_yaml_cleanup_on_error`); utána: 112 passed | alacsony — csak mock-célpont csere, nem üzleti logika |
| 9 | **ADOPT** (7a) + **PRESERVE** (7b/8a/8b): `project.schema.yaml` `compiler_settings` — felvett `repo_type` (enum `["schema","workflow","module"]`, most `required`), `main_branch`, `dependencies_dir`, `release_dir`, `cic_root_ca_secret_name`, `validity_days` (mind a `CIC-Schemas/project.schema.yaml:90,96-99,109-141`-ből). Megtartva: `compiler_settings.additionalProperties: false` (7b), top-level `required: [metadata, compiler_settings, abi]` + `additionalProperties: false` + `abi: $ref: "abi.schema.yaml"` (8a), `metadata` 9 extra mezője (8b, **változatlan, nem érintve**) | done | `git diff project.schema.yaml` (lent) | `pytest` → 112 passed (a `TestValidateFinalProjectYamlRealSchema` osztály is, lásd lent) | közepes — a `repo_type` `required`-be vétele miatt minden `project.yaml`-szerű instance-nak (élő + teszt-fixture) tartalmaznia kell `compiler_settings.repo_type`-ot, lásd 10. és a 8. tétel teszt-igazítása |
| 10 | **ADOPT**: `base-repo/project.yaml` `compiler_settings.repo_type: module` felvétele | done — **eltérés a riport induló feltételezésétől, dokumentálva** | `git diff project.yaml` (lent). **Megjegyzés**: a session elején véletlenül a `CIC-Schemas/project.yaml`-t grepeltem (ott már volt `repo_type: module`), és ez alapján "már kész"-nek jelöltem a lépést — ez **hibás** volt. A `base-repo/project.yaml`-ban **nem volt** `repo_type` mező a 9. lépés előtt; most felvéve. Emellett a `tests/test_tools/test_infra.py` `VALID_PROJECT_YAML_INSTANCE` fixture-jébe is felvettem `repo_type: module`-ot (ld. 8/9. tétel), különben a `TestValidateFinalProjectYamlRealSchema` 2 tesztje FAIL-elt volna a 9. lépés `required`-bővítése miatt | `pytest tests/test_tools/test_infra.py::TestValidateFinalProjectYamlRealSchema -q --no-cov` → 3 passed; teljes suite 112 passed | alacsony — additív mező, `_require_repo_type` sosem fut (6. tétel SKIP) |
| 11 | **`tools/compiler.py` validate-routing — NEM módosítva, futtatott bizonyíték alapján visszavonva a terv constraint #2 javaslata** | done — **a terv "nincs teendő" állítása megerősítve, de más indokkal; a constraint #2 routing-csere NEM ajánlott** | lásd "11. lépés — futtatott bizonyíték" szakasz lent | 3 db közvetlen Python hívás (`run_validation()`, `_validate_final_project_yaml()` OK projecten, `_validate_final_project_yaml()` FAIL üres `buildHash`-sal) | közepes — ld. indoklás lent |
| 12 | **Végső teszt-futtatás + manifest + make check** | done | `pytest tests/test_tools/ -q --no-cov` → **112 passed**; `black --check`, `isort --check-only`, `ruff check`, `yamllint`, `mypy`, `bandit` mind tiszta a módosított fájlokra; `MANIFEST.sha256` regenerálva és `sha256sum -c` zöld | lásd "12. lépés" szakasz lent | alacsony |

---

## Diff-ek

### `tools/infra.py` (1-3, 5-7. tétel)

```diff
@@ -1,20 +1,14 @@
 import base64
 import datetime
 import hashlib
-import json
 import logging
-import os
 import sys
-import tempfile
 from pathlib import Path

 import requests
 import yaml
-from jsonref import JsonRef
 from jsonschema import ValidationError as JsonSchemaValidationError
 from jsonschema import validate
-from OpenSSL import crypto
-from OpenSSL.SSL import Error as OpenSSLError

 from .releaselib.exceptions import (
     ConfigurationError,
@@ -22,105 +16,17 @@ from .releaselib.exceptions import (
     ReleaseError,
     VaultServiceError,
 )
+from .schemalib.artifact import (
+    build_signing_payload,
+    compute_spec_checksum,
+    parse_certificate_info,
+    to_canonical_json,
+)
+from .schemalib.loader import load_and_resolve_schema, load_yaml, write_yaml
+from .schemalib.validator import ValidationFailureError

-
-class ValidationFailureError(ReleaseError):
-    """Custom exception for schema validation failures."""
-
-    pass
-
-
-def to_canonical_json(data):
-    """Converts a Python object to a canonical (sorted, no whitespace) JSON string."""
-    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
-
-
-def get_sha256_hex(data_bytes):
-    """Calculates the SHA256 hash and returns it as a hex digest."""
-    return hashlib.sha256(data_bytes).hexdigest()
-
-
-def _parse_certificate_info(pem_cert_data):
-    """
-    Parses a PEM-encoded certificate to extract Common Name and Email.
-    Returns (name, email).
-    """
-    try:
-        cert = crypto.load_certificate(
-            crypto.FILETYPE_PEM, pem_cert_data.encode("utf-8")
-        )
-        subject = cert.get_subject()
-        name = subject.CN
-        email = None
-        for i in range(cert.get_extension_count()):
-            ext = cert.get_extension(i)
-            if ext.get_short_name() == b"subjectAltName":
-                alt_names = str(ext).split(", ")
-                for alt_name in alt_names:
-                    if alt_name.startswith("email:"):
-                        email = alt_name[len("email:") :]
-                        break
-        if not email:
-            email = subject.emailAddress
-        return name, email
-    except (OpenSSLError, Exception) as e:
-        logging.getLogger(__name__).warning(
-            f"Could not parse certificate with pyOpenSSL: {e}"
-        )
-        return "Unknown", "unknown@example.com"
-
-
-def load_and_resolve_schema(path):
-    """
-    Loads a YAML file and resolves all $ref references.
-    The base URI is the directory of the file, allowing for relative references.
-    """
-    try:
-        with open(path, "r") as f:
-            base_uri = f"file://{os.path.dirname(os.path.abspath(path))}/"
-            unresolved_data = yaml.safe_load(f)
-            resolved_data = JsonRef.replace_refs(unresolved_data, base_uri=base_uri)
-            return resolved_data
-    except FileNotFoundError as e:
-        raise ConfigurationError(f"File not found: {path}") from e
-    except yaml.YAMLError as e:
-        raise ConfigurationError(f"YAML parsing error in {path}: {e}") from e
-
-
-def load_yaml(path: Path):
-    """Loads a YAML file."""
-    try:
-        with open(path, "r") as f:
-            content = f.read()
-            if not content.strip():
-                return None
-            return yaml.safe_load(content)
-    except FileNotFoundError as e:
-        raise ConfigurationError(f"Configuration file not found at: {path}") from e
-    except yaml.YAMLError as e:
-        raise ConfigurationError(f"YAML syntax error in {path}: {e}") from e
-
-
-def write_yaml(path: Path, data):
-    """Writes data to a YAML file atomically."""
-    tmp_name = None
-    try:
-        with tempfile.NamedTemporaryFile(
-            mode="w", delete=False, dir=path.parent, encoding="utf-8"
-        ) as tmp_file:
-            tmp_name = tmp_file.name
-            yaml.dump(data, tmp_file, sort_keys=False, indent=2)
-        os.replace(tmp_name, path)
-    except (IOError, OSError) as e:
-        raise ReleaseError(f"Failed to write YAML file to {path}: {e}") from e
-    finally:
-        if tmp_name and Path(tmp_name).exists():
-            try:
-                Path(tmp_name).unlink()
-            except Exception as unlink_e:
-                logging.getLogger(__name__).warning(
-                    f"Failed to clean up temporary file {tmp_name}: {unlink_e}"
-                )
+# Back-compat alias for tests and external consumers
+_parse_certificate_info = parse_certificate_info


 class ReleaseManager:
@@ -243,8 +149,7 @@ class ReleaseManager:

             self.logger.info("Assembling the developer-stage project.yaml metadata...")

-            spec_bytes = to_canonical_json(source_data["spec"])
-            checksum = get_sha256_hex(spec_bytes)
+            checksum = compute_spec_checksum(source_data["spec"])
             self.logger.info(f"✓ Calculated spec checksum: {checksum[:12]}...")

             user_certificate = self.vault_service.get_certificate(
@@ -259,23 +164,15 @@ class ReleaseManager:
             )
             self.logger.info("✓ User and CIC Root CA certificates obtained from Vault.")

-            name, email = _parse_certificate_info(user_certificate)
-            self.logger.info(f"✓ Parsed user certificate: {name} <{email}>")
+            build_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
+            schema_name = source_data.get("metadata", {}).get("name", "unknown")

-            metadata_for_signing = {
-                "name": source_data.get("metadata", {}).get("name", "unknown"),
-                "version": release_version,
-                "checksum": checksum,
-                "build_timestamp": datetime.datetime.now(
-                    datetime.timezone.utc
-                ).isoformat(),
-            }
-
-            digest_bytes = to_canonical_json(metadata_for_signing)
-            digest_b64 = base64.b64encode(hashlib.sha256(digest_bytes).digest()).decode(
-                "utf-8"
+            digest_b64 = build_signing_payload(
+                name=schema_name,
+                version=release_version,
+                checksum=checksum,
+                build_timestamp=build_timestamp,
             )
-
             signature = self.vault_service.sign(
                 digest_b64, self.config["vault_key_name"]
             )
@@ -287,10 +184,10 @@ class ReleaseManager:
                 "version": release_version,
                 "checksum": checksum,
                 "sign": signature,
-                "build_timestamp": metadata_for_signing["build_timestamp"],
+                "build_timestamp": build_timestamp,
                 "createdBy": {
-                    "name": name,
-                    "email": email,
+                    "name": None,
+                    "email": None,
                     "certificate": user_certificate,
                     "issuer_certificate": cic_root_ca_cert,
                 },
@@ -298,6 +195,11 @@ class ReleaseManager:
                 "cicSign": "",
                 "cicSignedCA": {"certificate": ""},
             }
+            cert_name, cert_email = _parse_certificate_info(user_certificate)
+            metadata["createdBy"]["name"] = cert_name
+            metadata["createdBy"]["email"] = cert_email
+            self.logger.info(f"✓ Parsed user certificate: {cert_name} <{cert_email}>")
+
             project_data["metadata"] = metadata
             project_data["spec"] = source_data["spec"]
```

### `tools/finalize_release.py` (7. tétel)

```diff
@@ -18,7 +18,7 @@
 # (no Makefile/mk/*.mk/.github/workflows/*.yml call site — verified via
 # `grep -rn "finalize_release"`). The active release chain is
 # `make release` -> tools.compiler -> tools.infra.ReleaseManager
-# (see tools/infra.py:352-385 for the checksum+buildHash signing model).
+# (see tools/infra.py:254-287 for the checksum+buildHash signing model).
 # Track relay-readiness as a separate milestone; delete this module on
 # relay GA (cf. CIC-Schemas compiler-architecture-plan.md, "Step 10").
```

### `project.schema.yaml` (9. tétel: 7a/7b/8a/8b)

```diff
@@ -178,15 +178,23 @@ properties:
     type: object
     description: "Configuration for the build and release tools."
     required:
+      - repo_type
       - meta_schemas_dir
       - source_dir
       - meta_schema_file
       - vault_key_name
     additionalProperties: false
     properties:
+      repo_type:
+        type: string
+        description: "The type of repository. Controls which compiler commands are available."
+        enum: ["schema", "workflow", "module"]
       component_name:
         type: string
         description: "Release component name (tools/infra.py: _check_base_branch_and_version)."
+      main_branch:
+        type: string
+        description: "The target branch for merge-back after release."
       meta_schemas_dir:
         type: string
       meta_schema_file:
@@ -194,6 +202,12 @@ properties:
       canonical_source_file:
         type: string
         description: "The canonical source schema validated by `make validate` (tools/infra.py: run_validation)."
+      dependencies_dir:
+        type: string
+        description: "Directory for validator schemas (schema repos only)."
+      release_dir:
+        type: string
+        description: "Output directory for released schemas (schema repos only)."
       vault_key_name:
         type: string
         description: "The Vault key name for the author's signature."
@@ -211,6 +225,12 @@ properties:
       vault_cert_secret_key:
         type: string
         description: "Vault secret key for the author's/CIC Root CA certificate."
+      cic_root_ca_secret_name:
+        type: string
+        description: "Secret name in Vault KV for the CIC Root CA certificate."
+      validity_days:
+        type: integer
+        description: "How many days a release artifact remains valid."

   abi:
     $ref: "abi.schema.yaml"
```

### `project.yaml` (10. tétel)

```diff
@@ -42,6 +42,7 @@ metadata:
   cicSignedCA:
     certificate: "TBD — filled by the release process with the CIC Root CA certificate"
 compiler_settings:
+  repo_type: module
   component_name: wasm-module
   meta_schemas_dir: ./
   meta_schema_file: md.meta.schema.yaml
```

### `tests/test_tools/test_infra.py` / `test_infra_coverage.py` (8., 9-10. tétel)

```diff
--- a/tests/test_tools/test_infra.py
+++ b/tests/test_tools/test_infra.py
@@ -101,7 +101,9 @@ class TestHelperFunctions:
         mock_cert.get_extension_count.return_value = 1
         mock_cert.get_extension.return_value = mock_ext

-        mocker.patch("tools.infra.crypto.load_certificate", return_value=mock_cert)
+        mocker.patch(
+            "tools.schemalib.artifact.crypto.load_certificate", return_value=mock_cert
+        )
         name, email = _parse_certificate_info(VALID_CERT)
         assert name == "Test User"
         assert email == "alt@email.com"
@@ -114,7 +116,9 @@ class TestHelperFunctions:
         mock_cert.get_subject.return_value = mock_subject
         mock_cert.get_extension_count.return_value = 0  # No extensions

-        mocker.patch("tools.infra.crypto.load_certificate", return_value=mock_cert)
+        mocker.patch(
+            "tools.schemalib.artifact.crypto.load_certificate", return_value=mock_cert
+        )
         name, email = _parse_certificate_info(VALID_CERT)
         assert name == "Test User"
         assert email == "fallback@email.com"
@@ -299,6 +303,7 @@ metadata:
   owner: Gabor Zoltan Sinko
   buildHash: deadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00d
 compiler_settings:
+  repo_type: module
   component_name: wasm-module
   meta_schemas_dir: ./
   meta_schema_file: md.meta.schema.yaml

--- a/tests/test_tools/test_infra_coverage.py
+++ b/tests/test_tools/test_infra_coverage.py
@@ -90,13 +90,17 @@ class TestInfraCoverage:
         mock_tmp_file = MagicMock()
         mock_tmp_file.name = "/fake/dir/temp123"
         mocker.patch(
-            "tools.infra.tempfile.NamedTemporaryFile", return_value=mock_tmp_file
+            "tools.schemalib.loader.tempfile.NamedTemporaryFile",
+            return_value=mock_tmp_file,
+        )
+        mocker.patch(
+            "tools.schemalib.loader.os.replace",
+            side_effect=OSError("permission denied"),
         )
-        mocker.patch("tools.infra.os.replace", side_effect=OSError("permission denied"))

         mock_path_instance = MagicMock()
         mock_path_instance.exists.return_value = True
-        mocker.patch("tools.infra.Path", return_value=mock_path_instance)
+        mocker.patch("tools.schemalib.loader.Path", return_value=mock_path_instance)

         with pytest.raises(ReleaseError):
             write_yaml(Path("any.yaml"), {})
```

---

## Pytest-futások

### 1-8. lépés után (import-csere + dup. törlés + dev-prep átírás, 2 teszt-igazítás előtt)

```
$ python3 -m pytest tests/test_tools/ -q --no-cov
collected 112 items
...
FAILED tests/test_tools/test_infra.py::TestHelperFunctions::test_parse_certificate_info_with_alt_name
FAILED tests/test_tools/test_infra.py::TestHelperFunctions::test_parse_certificate_info_fallback_email
FAILED tests/test_tools/test_infra_coverage.py::TestInfraCoverage::test_write_yaml_cleanup_on_error
3 failed, 109 passed in 0.65s
```

Ok kivizsgálva: mindhárom a `crypto`/`tempfile`/`os`/`Path` modul-szintű
import megszűnése `tools.infra`-ból (most `tools.schemalib.artifact`/
`tools.schemalib.loader`-ben élnek) — patch-cél javítva (8. tétel).

### 1-8. lépés után, teszt-igazítással

```
$ python3 -m pytest tests/test_tools/ -q --no-cov
collected 112 items
tests/test_tools/test_compiler.py ...........                            [  9%]
tests/test_tools/test_finalize_release.py ...................            [ 26%]
tests/test_tools/test_infra.py .................                         [ 41%]
tests/test_tools/test_infra_coverage.py ..............                   [ 54%]
tests/test_tools/test_releaselib/test_git_service.py ................... [ 71%]
...........                                                              [ 81%]
tests/test_tools/test_releaselib/test_vault_service.py ................. [ 96%]
....                                                                     [100%]
112 passed in 0.45s
```

### 9. lépés után, 10. lépés (project.yaml `repo_type`) előtt

```
$ python3 -m pytest tests/test_tools/ -q --no-cov
collected 112 items
...
FAILED tests/test_tools/test_infra.py::TestValidateFinalProjectYamlRealSchema::test_real_schema_accepts_valid_project_yaml
FAILED tests/test_tools/test_infra.py::TestValidateFinalProjectYamlRealSchema::test_real_schema_rejects_empty_build_hash
2 failed, 110 passed in 0.51s
```

Hiba: `jsonschema.exceptions.ValidationError: 'repo_type' is a required
property` — a `VALID_PROJECT_YAML_INSTANCE` test-fixture `compiler_settings`
blokkjában nem volt `repo_type`. Javítva (10. tétel: `repo_type: module`
felvétele a fixture-be is).

### 9-10. lépés után (végleges)

```
$ python3 -m pytest tests/test_tools/ -q --no-cov
collected 112 items
tests/test_tools/test_compiler.py ...........                            [  9%]
tests/test_tools/test_finalize_release.py ...................            [ 26%]
tests/test_tools/test_infra.py .................                         [ 41%]
tests/test_tools/test_infra_coverage.py ..............                   [ 54%]
tests/test_tools/test_releaselib/test_git_service.py ................... [ 71%]
...........                                                              [ 81%]
tests/test_tools/test_releaselib/test_vault_service.py ................. [ 96%]
....                                                                     [100%]
112 passed in 0.48s
```

---

## 11. lépés — futtatott bizonyíték

A terv szerinti "Előre eldöntött korlát #2" állítása: `validate` subcommand
hívjon `_validate_final_project_yaml()`-t `manager.run_validation()` helyett,
mert az utóbbi no-op placeholder.

**1. `run_validation()` viselkedése** (futtatva `dry_run=True`, valós
`schemas/index.yaml`-on):

```
--- Running Schema Validation ---
Validating and resolving .../base-repo/schemas/index.yaml...
Schema 'template-schema' loaded.
✓ Schema validation logic to be fully implemented here.
✓ Validation successful.
```

→ **megerősítve**: `run_validation()` valóban no-op — nem hív
`jsonschema.validate`-et semmilyen schema ellen, csak betölti és feloldja a
`canonical_source_file`-t, majd mindig "✓ Validation successful"-t logol.

**2. `_validate_final_project_yaml()` a jelenlegi (9-10. lépés utáni)
`project.yaml`-on**:

```
Validating final project.yaml against schema...
✓ project.yaml is valid against the schema.
```

→ a 9-10. lépés migrációja **nem törte** a valós `project.yaml`/
`project.schema.yaml` validációt.

**3. `_validate_final_project_yaml()` egy "pre-build" (üres `buildHash`)
`project.yaml`-on**, ami a `make wasm.build` előtti, frissen generált
template állapotot szimulálja:

```
FAILED (pre-build, empty buildHash): metadata.buildHash is required and
must be non-empty before finalization — run 'make wasm.build' to populate it.
```

### Döntés

**A `tools/compiler.py` `validate` routing-ját NEM módosítom** — a terv
constraint #2 javaslatát **futtatott bizonyíték alapján visszavonom**:

- `run_validation()` és `_validate_final_project_yaml()` **két különböző
  validációs célt szolgálnak**: az előbbi a `compiler_settings.
  canonical_source_file`-t (a schema-repo saját spec-forrását, itt
  `schemas/index.yaml`) validálná, az utóbbi a release-finalizáció
  előfeltételeként a **végleges** `project.yaml`-t (incl. kötelező,
  nem-üres `metadata.buildHash`) ellenőrzi a `project.schema.yaml` ellen.
- Ha a `validate` subcommand `_validate_final_project_yaml()`-t hívná,
  a `make validate` **minden, `make wasm.build` előtt álló friss
  template-en elbukna** (`metadata.buildHash is required and must be
  non-empty before finalization`) — ez **regresszió** lenne a `make
  validate`-nek a Makefile help-szövege szerinti ("Run fast, offline
  validation of all schemas") céljához képest, és a wasm-template
  generálási workflow-t (generate → validate → build → finalize) törné.
- `_validate_final_project_yaml()` már most is meghívásra kerül a
  release-finalizáció részeként (`_execute_finalization_phase:289` →
  `:308`-nál) — a `validate` subcommandba duplikálása redundáns lenne a
  release-úton, és káros a pre-build úton.
- `run_validation()` **valóban no-op placeholder** — ez igaz marad, de a
  helyes javítás **nem** a `_validate_final_project_yaml()`-re való
  átirányítás, hanem `run_validation()` saját, érdemi implementációja
  (pl. a `canonical_source_file`-t egy megfelelő meta-schema ellen
  validálni) — ez **a 6. tétel SKIP döntésével konzisztens módon**, külön
  (jövőbeli) feladat, nem ennek a job-nak a hatóköre.
- **Funkció nem törölve**: `run_validation()` és `_validate_final_project_yaml()`
  egyaránt megmaradt, hívási helyük változatlan.

`tools/compiler.py`: **0 sor módosítva**.

---

## 12. lépés — manifest + make check

### `make manifest-update` / `make manifest-verify` (lokális, Docker builder
nem elérhető a job workspace-ből — lásd indoklás lent)

```
$ git ls-files -z | xargs -0 sha256sum | grep -v "MANIFEST.sha256" \
    | LC_ALL=C sort > MANIFEST.sha256
$ sha256sum -c MANIFEST.sha256 | grep -v ": OK"
(nincs kimenet — minden fájl OK)
```

A `MANIFEST.sha256` diffje csak a módosított fájlok (`tools/infra.py`,
`tools/finalize_release.py`, `project.yaml`, `project.schema.yaml`,
`tests/test_tools/test_infra.py`, `tests/test_tools/test_infra_coverage.py`)
hash-eit, illetve a már korábban (PR #17-ben transzferált, de a MANIFEST-ben
korábban más sorrendben szereplő) `tools/schemalib/*` fájlok újrarendezését
érinti — utóbbiak hash-e nem változott, csak a `sort` pozíciójuk.

### `make check` (black / isort / ruff / yamllint / mypy / bandit) — lokális
venv-ben (`/tmp/wasm-infra-venv`), a `docker compose exec builder` helyett
(lásd alább)

```
$ python -m black --check tools/infra.py tools/finalize_release.py \
    tests/test_tools/test_infra.py tests/test_tools/test_infra_coverage.py
# (1. futás: "would reformat" a 2 módosított teszt-fájlra → black
#  futtatva, 2 fájl reformázva, utána --check zöld)

$ python -m isort --skip-glob "p_venv/*" --check-only \
    tools/infra.py tools/finalize_release.py \
    tests/test_tools/test_infra.py tests/test_tools/test_infra_coverage.py
(exit 0)

$ python -m ruff check tools/infra.py tools/finalize_release.py \
    tests/test_tools/test_infra.py tests/test_tools/test_infra_coverage.py
All checks passed!

$ python -m yamllint project.schema.yaml project.yaml
(nincs kimenet — zöld)

$ python -m mypy --exclude p_venv tools/
Success: no issues found in 14 source files

$ python3 -m bandit -r tools
Run metrics:
    Total issues (by severity): Undefined: 0, Low: 0, Medium: 0, High: 0
```

**Docker indoklás**: a workspace-ben futó `base-repo-builder-1` konténer egy
**másik job munkaterületéhez** tartozik (5 órás uptime, eltérő bind-mount
forrás) — a `docker compose project name` (`base-repo`, a könyvtárnév
alapján) ütközne vele, ezért a `docker compose exec builder` futtatása ezt a
megosztott konténert érintette volna. A lokális venv (`/tmp/wasm-infra-venv`,
Python 3.12.3, a `wasm-infra-migration-plan` job által létrehozva, ugyanazokkal
a `requirements.txt`-ből telepített verziókkal: black 25.11.0, isort, ruff
0.14.4, mypy 1.18.2, bandit 1.9.2) ugyanazokat a parancsokat futtatja, mint a
`mk/infra.mk` `infra.fmt`/`infra.lint`/`infra.typecheck`/`infra.security`
target-jei — ez a korábbi (`wasm-infra-migration-plan`,
`wasm-schemalib-transfer`) job-ok bevett gyakorlata is.

### Végső pytest

```
$ python3 -m pytest tests/test_tools/ -q --no-cov
112 passed in 0.48s
```

---

## Összefoglaló

### Módosított fájlok (`base-repo`, `wasm/f/infra-migration`)

| Fájl | Változás |
|---|---|
| `tools/infra.py` | -150/+74 sor — schemalib-importok adoptálása, dup. primitívek törlése, `_execute_developer_preparation_phase` átírása (checksum/signing/createdBy) |
| `tools/finalize_release.py` | DEPRECATED komment sorhivatkozás frissítve `352-385` → `254-287` |
| `project.schema.yaml` | `compiler_settings`: `repo_type` (új, `required`) + 5 additív mező (`main_branch`, `dependencies_dir`, `release_dir`, `cic_root_ca_secret_name`, `validity_days`); `additionalProperties: false`, top-level `required`/`abi` $ref, `metadata` 9 extra mező **változatlan** |
| `project.yaml` | `compiler_settings.repo_type: module` felvéve |
| `tests/test_tools/test_infra.py` | 2 mock-célpont javítva (`tools.infra.crypto` → `tools.schemalib.artifact.crypto`); `VALID_PROJECT_YAML_INSTANCE` fixture: `repo_type: module` felvéve |
| `tests/test_tools/test_infra_coverage.py` | 3 mock-célpont javítva (`tools.infra.{tempfile,os,Path}` → `tools.schemalib.loader.{tempfile,os,Path}`) |
| `MANIFEST.sha256` | regenerálva |

Commitok (`wasm/f/infra-migration`, `b7da285`-ről):
1. `c382e5e` — `refactor(infra): adopt schemalib primitives in ReleaseManager`
2. `06dc7c2` — `feat(schema): sync compiler_settings with CIC-Schemas project.schema.yaml`
3. `068ceae` — `chore: regenerate MANIFEST.sha256 after infra/schema migration`

### `CentralInfraCore/base-repo#16`, 3-6. lépés státusza ezután

A `wasm-infra-migration-plan` riport scope-ja a `tools/infra.py`/
`tools/compiler.py`/`project.schema.yaml` migráció (issue #16 3-6. lépése
— "teszt igazítások" a 6. pont SKIP-jéhez kötve). Ez a job:

- **3-5. lépést** (a tervben 1-10. tétel) **teljesen lefedte** — `infra.py`
  immár a transzferált `schemalib`-et használja, duplikáció megszűnt,
  `project.schema.yaml`/`project.yaml` szinkronban van `CIC-Schemas`-szal a
  wasm-specifikus PRESERVE-réteg megtartásával.
- **6. lépés** ("teszt igazítások", a SKIP döntéshez kötve): a SKIP-elt
  `_get_repo_type`/`_require_repo_type`/`run_release_dependency`/
  `run_release_schema`/`_execute_schema_release` metódusok **nem** kerültek
  át (megerősítve, `grep` 0 találat `base-repo`-ban, változatlanul). A
  hozzájuk kapcsolódó tesztek (ha lennének) — nincsenek, mert a metódusok
  nem kerültek át, így nincs "elmaradt teszt-igazítás" ezen a téren.
- **Nyitott pont nincs** a 3-6. lépésre vonatkozóan ezen job hatókörén
  belül — a 11. tételhez kapcsolódó `run_validation()` no-op-státusz
  **dokumentált, de szándékosan nem javított** kérdés (külön jövőbeli
  feladat, lásd a 11. lépés indoklása), ez **nem** blokkolja a #16 issue
  3-6. lépésének lezárását ezen a migrációs szálon.

### Önellenőrzés

- [x] 1-12. lépés sorrendben végrehajtva, eltérések dokumentálva (4., 6.,
  8., 10., 11. tételnél)
- [x] Minden ADOPT-lépésnél diff + pytest-output
- [x] 31/31 (illetve a teljes 112/112) PASS minden lépés-csoport után
- [x] `make manifest-update`/`-verify` + `make check` (lokális
  venv-ekvivalens) zöld
- [x] 11. lépés döntése + futtatott bizonyíték (3 script-futás)
- [x] Módosított fájlok listája + issue #16 3-6. lépés státusza
- [x] `base-repo`: 3 commit, pusholva `wasm/f/infra-migration`-ra
- [ ] `cic-factory`: riport pusholva `feature/wasm-infra-migration-impl`-ra
  (következő lépés)
