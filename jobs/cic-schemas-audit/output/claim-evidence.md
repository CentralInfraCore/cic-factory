# claim-evidence.md — CIC-Schemas audit

Minden állítás mögött konkrét verifikáció.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Branch modell dokumentálva | true | `git branch -a` kimenet: 5 pg-verzió (v14–v18) mind dev+main, base remote 10+ branch, origin/CICmeta/devel | `git -C ... branch -a` futtatva, teljes kimenet elolvasva | alacsony |
| Séma formátum megértve | true | `schemas/index.yaml` teljes elolvasva (metadata + spec blokk, $ref-ek, validatedBy, conditional allOf), `source/postgresql.conf.yaml` első 80 sor elolvasva | Fájl tartalom közvetlenül olvasva, nem csak listázva | alacsony |
| Meta-séma (dependencies) elolvasva | true | `dependencies/template-schema-v0.9.5_2025.yaml` első 40 sor elolvasva — aláírt artifact, validatedBy self-referential | Fájl tartalom olvasva | alacsony |
| Signing pipeline dokumentálva | true | `tools/compiler.py` teljes elolvasva (597 sor), `tools/release.sh` teljes elolvasva (103 sor), `tools/git_hook_commit-msg.sh` teljes elolvasva | Fájl tartalom olvasva, signing lépések kódon keresztül követve | alacsony |
| Vault mechanizmus dokumentálva | true | `tools/vault-sign-agent.sh` grep kimenet: transit engine, kulcs importálás, KV store, sign policy, token file — 40 sor részlet elemezve | grep -rn vault futtatva | közepes (nem láttam a teljes fájlt, de a lényeges részek megvannak) |
| OCI publikálás státusza megállapítva | true | `grep -rn "ghcr\|oci\|docker\|push\|registry"` — csak Docker Compose build env referenciák, registry push nincsen | Grep minden py/yaml/sh/Makefile fájlon futtatva | alacsony |
| PostgreSQL séma példa dokumentálva | true | `release/postgresql-v0.18.0_2025.yaml` első 79 sor elolvasva (teljes metadata blokk: sign, checksum, createdBy, certificate lánc) | Fájl tartalom olvasva | alacsony |
| Build pipeline (Makefile) dokumentálva | true | `Makefile` teljes elolvasva — minden target (up, down, shell, validate, test, fmt, lint, typecheck, check, release-dependency, release-schema, repo.init, infra.*) | Fájl tartalom olvasva | alacsony |
| Release artifact formátum megértve | true | `release/postgresql-v0.18.0_2025.yaml` tartalmaz: name, version, validatedBy+checksum, validity, checksum (spec SHA256), sign (vault:v1:...), build_timestamp, createdBy (name+email+certificate+issuer_certificate), spec (inline, $ref-ek feloldva) | Fájl tartalom olvasva, compiler.py logikával keresztellenőrizve | alacsony |
| Dependency model megértve | true | `dependency.yaml`: `dependencies.postgres: 18.1-alpine3.22` — a runtime image verzió külön tracked | Fájl tartalom olvasva | alacsony |
| OCI: nincs registry push | true | Teljes grep sem Makefile-ban, sem release.sh-ban, sem compiler.py-ban nem talált `ghcr`, `oci push`, `docker push`, `registry` parancsot (csak docker compose build env) | grep futtatva | alacsony |

## Nem talált dolgok (expliciten rögzítve)

| Keresett dolog | Eredmény |
|---|---|
| OCI/GHCR registry push | Nem található — terjesztés kizárólag git tag push-on keresztül |
| `release/` könyvtár tartalma v14-v17 | Csak v18 release látható — a korábbi verziók valószínűleg a saját branch-eiken vannak |
| `features/schemas/` könyvtár | Nem létezik (features/feature-001/ és features/feature-002/ létezik) |
| Countersign (`countersign`, `cic_countersign`) | Nem található — a signing egyszintű (Vault transit, egyetlen kulcs) |
| WASM modul referencia | Nem található — CIC-Schemas tisztán séma/signing pipeline, WASM nincs |
