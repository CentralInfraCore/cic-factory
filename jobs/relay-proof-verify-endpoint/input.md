# relay-proof-verify-endpoint — POST /v1/proof/verify HTTP endpoint

## Háttér

A CIC-Relay tartalmazza a `VerifyProofArtifact` függvényt (`core/cabinet/`), de nincs publikus HTTP endpoint rá. A demo narratívához kritikus: a ProofTrace chain_hash-t vissza kell tudni ellenőrizni HTTP-n keresztül.

**Cél:** `POST /v1/proof/verify` endpoint, ami egy ProofArtifact-ot fogad és visszaadja az ellenőrzés eredményét.

## Forrás

```
${CIC_RELAY_PATH}/cmd/relay/          ← handler-ek, routing
${CIC_RELAY_PATH}/core/cabinet/       ← VerifyProofArtifact, ProofArtifact típus
```

Először olvasd el:

```bash
grep -rn "VerifyProofArtifact\|ProofArtifact\|ProofTrace" ${CIC_RELAY_PATH}/core/cabinet/ --include="*.go" | grep -v "_test.go"
grep -rn "v1/schema\|v1/proof\|HandleFunc\|router\|mux" ${CIC_RELAY_PATH}/cmd/relay/ --include="*.go" | grep -v "_test.go"
```

## Elvárt viselkedés

**Request:**
```json
POST /v1/proof/verify
Content-Type: application/json

{
  "proof_artifact": { ... }
}
```

**Response (valid):**
```json
{
  "valid": true,
  "warnings": []
}
```

**Response (invalid):**
```json
{
  "valid": false,
  "warnings": ["chain hash mismatch: expected abc123, got def456"]
}
```

## Elvégzendő lépések

1. Olvasd el `VerifyProofArtifact` szignatúráját és a `ProofArtifact` struktúrát
2. Nézd meg a meglévő handler-ek struktúráját (pl. `/v1/schema/compile`) — kövesd a mintát
3. Implementáld a handler-t és regisztráld a router-ben
4. Írj legalább egy tesztet a handler-re (sikeres verify + hibás chain hash eset)
5. Futtasd a teszteket:

```bash
cd ${CIC_RELAY_PATH}
COMPOSE_FILE=docker-compose.yaml docker compose up -d builder
COMPOSE_FILE=docker-compose.yaml make test-go
```

6. Ha tesztek zöldek: commit + push

```bash
git -C ${CIC_RELAY_PATH} checkout -b feat/proof-verify-endpoint
git -C ${CIC_RELAY_PATH} add cmd/relay/
git -C ${CIC_RELAY_PATH} commit -m "feat(api): POST /v1/proof/verify — chain hash verification endpoint"
git -C ${CIC_RELAY_PATH} push -u origin feat/proof-verify-endpoint
```

## Output fájlok

`output/endpoint-report.md`:

```markdown
## VerifyProofArtifact szignatúra
[grep kimenet]

## Implementált handler
**Fájl:** cmd/relay/[fájlnév]
**Függvény:** [handler neve]
**Router regisztráció:** [sor ahol be van kötve]

## Teszt
**Tesztfájl:** [path]
**Tesztesetek:** [lista]
**Exit code:** 0 / 1

## Git
**Branch:** feat/proof-verify-endpoint
**Commit hash:** ...
```

`output/claim-evidence.md` — Kötelező tábla:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| VerifyProofArtifact meghívható HTTP handler-ből | true/false | grep: szignatúra + handler kód | grep + kód olvasva | kritikus |
| /v1/proof/verify route regisztrálva | true/false | grep a router fájlban | grep -rn futtatva | kritikus |
| handler tesztek zöldek | true/false | exit code + PASS sorok | make test-go futtatva | kritikus |
| változások commitolva | true/false | commit hash | git log | alacsony |

## Szabályok

- **Fájl létezése ≠ implementált** — grep-pel ellenőrizd a route regisztrációt
- **Exit code 0 ≠ sikeres** — olvasd el a teszt kimenetét
- Kövesd a meglévő handler mintát — ne vezess be új függőségeket
- Ha `VerifyProofArtifact` signature nem HTTP-kompatibilis: rögzítsd és jelezd, ne wrapper-ezd erőltetetten
- Legalább 1 sikeres + 1 hibás eset tesztje szükséges
