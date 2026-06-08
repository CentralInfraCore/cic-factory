# poc-schema-design — PoC séma tervezése

## Célod

Tervezd meg a CIC PoC sémáját: egy konkrét `poc/v1` branch struktúrát a CIC-Schemas repóhoz,
amely kombinálja a CIC-Schemas meglévő formátumát a primitives `cic_countersign` blokkjával,
és amelyet a CIC-Relay közvetlenül tudja fogadni és verifikálni.

**Ez nem implementáció** — design document és konkrét minta YAML artifact.

---

## Kontextus — mit tudunk már

### CIC-Schemas formátum (cic-schemas-audit alapján)

Két blokk: `metadata` + `spec`. A release artifactban:

```yaml
metadata:
  name: postgresql
  version: v0.18.0_2025
  validatedBy:
    name: template-schema
    version: v0.9.5_2025
    checksum: <meta-séma spec SHA256>
  checksum: <spec blokk SHA256>
  sign: vault:v1:<base64>            # Vault transit ECDSA P-256
  build_timestamp: '2025-11-18T16:29:10Z'
  createdBy:
    name: Gabor Zoltan Sinko
    email: sgz@centralinfracore.hu
    certificate: "-----BEGIN CERTIFICATE-----\n..."
    issuer_certificate: "-----BEGIN CERTIFICATE-----\n..."
spec:
  type: object
  # ... feloldott JSON Schema
```

### primitives cic_countersign formátum (v0.1.5 alapján)

A `PrimitiveRelease` artifact végén:

```yaml
cic_countersign:
  certificate: "Certificate:\n  Data:\n  ..."    # CICSourceCA leaf cert (text format)
  root_certificate: "-----BEGIN CERTIFICATE-----\n..."   # Root PEM
  signed_payload: build_hash                             # mi lett aláírva
  sign: vault:v1:<base64>                                # CICSourceCA aláírása
```

A primitives `cic_sign.sh` OpenSSL direkt hívással ír alá (`openssl pkeyutl -sign`),
nem Vault transit-tel — de az aláírás formátuma azonos: `vault:v1:<base64>`.

### Eldöntött arch döntések

| Kérdés | Döntés |
|---|---|
| Q1: Trust anchor | Minden obj source-jában benne a CICSource ellenjegyzés + PEM-je |
| Q2: IaCSource | git-tag alapú (`postgresql@v0.18.0_2025`), nem OCI |
| Q3: TrustAnchorRegistry | Nincs külön registry — a PEM az objban, CA-tól való eredet elegendő |
| Q4: Ellenjegyzés kötelesség | Igen, minden obj-hoz kell — a primitives formátuma ezt mutatja |
| Q5: Notice trigger | Module-onként notice endpoint, stateless, incron/scheduler/service triggeri |

### CIC-Relay jelenlegi állapot

- `POST /v1/proof` — Wasm aktiváció, spec alapján
- `POST /v1/proof/verify` — új endpoint (megvalósítva, feature branch-re commitolva)
- A relay fogadja a `spec`-et — de még nem ellenőrzi a `sign`-t és `checksum`-t
- A relay-nek kell majd: schema pull (git), checksum verify, sign verify

---

## Forrás repók (olvasásra, módosítás tilos)

```
${CIC_SCHEMAS_PATH}              ← CIC-Schemas repó
${CIC_SCHEMAS_PATH}/release/postgresql-v0.18.0_2025.yaml   ← referencia release artifact
```

Primitives release referencia (olvasásra):
```
/home/sinkog/sync/git.partners/CentralInfraCore/primitives-group/primitives/release/cic-primitives-v0.1.5.yaml
```

---

## Lépések

### 1. Meglévő release artifact mélyolvasása

Olvasd el a CIC-Schemas postgresql release artifactot:
```bash
cat ${CIC_SCHEMAS_PATH}/release/postgresql-v0.18.0_2025.yaml
```

Olvasd el a primitives release artifactot (cic_countersign blokk):
```bash
cat /home/sinkog/sync/git.partners/CentralInfraCore/primitives-group/primitives/release/cic-primitives-v0.1.5.yaml
```

Azonosítsd:
- Pontosan milyen mezők vannak a `cic_countersign` blokkban
- Hogyan épül fel a `certificate` mező (text vs PEM)
- Mi a `signed_payload` értéke (mi lett ténylegesen aláírva)

### 2. PoC séma terv — struktúra

Tervezd meg a `poc/v1` branch struktúráját a CIC-Schemas repóban.

A PoC sémának:
- Egyszerű legyen — **nem PostgreSQL**, hanem egy minimális "cic-relay-config" séma
  (ez a relay saját konfigurációjának sémája, amit maga is tud validálni)
- Kövesse a CIC-Schemas formátumot (`metadata` + `spec`)
- Tartalmazzon `cic_countersign` blokkot (a primitives mintájára)
- Legyen verifikálható a relay által

A `spec` tartalma: a relay input format sémája —
```yaml
spec:
  type: object
  required: [relay_id, version, trust_level]
  properties:
    relay_id:
      type: string
      description: "Unique relay instance identifier"
    version:
      type: string
      pattern: "^v[0-9]+\\.[0-9]+"
    trust_level:
      type: string
      enum: [L0, L1, L2, L3, L4, L5, L6, L7]
    modules:
      type: array
      items:
        type: string
```

### 3. PoC séma — teljes minta artifact

Állíts össze egy **teljes, konkrét** PoC release artifact YAML-t:

- `metadata.name: cic-relay-config`
- `metadata.version: v0.1.0_poc`
- `metadata.validatedBy`: hivatkozzon egy `template-schema v0.9.5_2025`-re
  (a checksum-ot töltsd ki placeholder értékkel: `<TEMPLATE_SCHEMA_CHECKSUM>`)
- `metadata.checksum`: `<SPEC_SHA256>` placeholder
- `metadata.sign`: `vault:v1:<RELAY_SIGN>` placeholder
- `metadata.createdBy`: töltsd ki reális értékekkel ahol ismert
- `spec`: a fenti relay-config schema
- `cic_countersign`:
  - `certificate`: milyen formátumban (text vs PEM) — a primitives alapján döntsd el
  - `root_certificate`: PEM placeholder
  - `signed_payload`: mi legyen aláírva (checksum? metadata SHA256? build_hash?)
  - `sign`: `vault:v1:<COUNTERSIGN>` placeholder

**Fontos döntés a `signed_payload`-ről:**
A CIC-Schemas-ban a `sign` a metadata SHA256-ját írja alá.
A primitives `cic_countersign` a `build_hash`-t írja alá.
Döntsd el: a PoC-ban mi legyen a `cic_countersign signed_payload`-ja — és indokold meg.

### 4. Relay integráció terv

Dokumentáld, hogyan kell a relay-nek kezelnie ezt a sémát:

**Séma betöltés:**
```
git pull ${CIC_SCHEMAS_PATH} → release/<name>-<version>.yaml → beolvasás
```

**Verifikáció sorrendje:**
1. `checksum` ellenőrzés: `spec` blokk SHA256 újraszámítva == `metadata.checksum`?
2. `sign` ellenőrzés: Vault `/v1/transit/verify/cic-my-sign-key` hívás
3. `cic_countersign` ellenőrzés: CICSourceCA cert → public key kinyerés → ECDSA verify

Melyik lépés szükséges a PoC-hoz minimum? Melyik hagyható scaffoldra?

### 5. Branch struktúra javaslat

Tervezd meg a `poc/v1` branch tartalmát a CIC-Schemas repóban:

```
poc/v1/
  schemas/index.yaml          ← séma forrás (nem feloldott)
  source/relay-config.yaml    ← JSON Schema fragment
  release/cic-relay-config-v0.1.0_poc.yaml  ← signed release artifact (placeholder)
  tools/                      ← szimlink vagy copy a base-ből?
  Makefile                    ← szimlink vagy copy a base-ből?
```

---

## Output fájlok

### `output/poc-schema-design.md`

```markdown
## Séma struktúra döntések
[milyen mezők, miért, eltérés a CIC-Schemas-tól]

## cic_countersign integráció
[hogyan illeszkedik a CIC-Schemas formátumba, signed_payload döntés és indok]

## Relay verifikációs sorrend
[lépések sorrendben, mi PoC-minimum és mi scaffold]

## poc/v1 branch terv
[mit kell létrehozni, mit lehet szimlinkelni a base-ből]

## Nyitott kérdések
[amit nem lehet dönteni a rendelkezésre álló info alapján]
```

### `output/poc-schema-example.yaml`

Teljes, konkrét, futtatható minta — placeholder értékekkel ahol valódi aláírás kell.
Ez legyen `valid YAML` szintaktikailag.

### `output/relay-integration-plan.md`

A relay-side integrációs terv:
- Melyik Go fájlba kerül a schema verifikáció
- Milyen interface-t célszerű felvenni (schema loader, verifier)
- Mi a PoC minimum (checksum verify) és mi scaffold (Vault verify, CA verify)

### `output/claim-evidence.md`

Kötelező tábla:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| postgresql release artifact elolvasva | true/false | fájl path, jellemző mező nevei | cat output | alacsony |
| primitives cic_countersign struktúra megértve | true/false | mező nevek + típusok | cat + elemzés | közepes |
| signed_payload döntés megalapozott | true/false | indoklás hivatkozással | összehasonlítás | kritikus |
| poc-schema-example.yaml valid YAML | true/false | yaml.safe_load() sikeres | python3 -c "import yaml; yaml.safe_load(open(...))" | kritikus |
| relay integrációs terv konkrét Go fájlra mutat | true/false | fájl path a CIC-Relay-ben | ls/grep | közepes |

---

## Szabályok

- **Fájl létezése ≠ megértve** — olvasd el, ne csak listázd
- **Placeholder értékek helyesen jelölve** — `<NAGYBETŰS_PLACEHOLDER>` formátum
- **Döntés = indoklás** — minden döntési pont mellé írj 1-2 mondatos indokot
- Ne módosíts semmit a CIC-Schemas vagy primitives repókban
- A `poc-schema-example.yaml` legyen valid YAML — ellenőrizd Python yaml.safe_load()-dal
