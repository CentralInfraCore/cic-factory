# relay-full-build — Teljes build Vaulttal (make build-relay)

## Háttér

A `relay-build-test` job kimutatta, hogy a `make build-relay` a `fetch-pki` lépésnél megáll: `VAULT_TOKEN: unbound variable`. A Vault szerver valószínűleg fut (sign-token fájl létezik), csak a `VAULT_TOKEN` env variable nincs exportálva.

## Célod

A `make build-relay` teljes pipeline futtatása Vault tokennel, és a keletkező bináris verifikálása.

## Forrás

CIC-Relay repo: `${CIC_RELAY_PATH}`
Vault token fájl: `${XDG_RUNTIME_DIR}/vault/sign-token` (ha létezik)

## Előkészítés

```bash
# Vault token betöltése
export VAULT_TOKEN=$(cat ${XDG_RUNTIME_DIR}/vault/sign-token 2>/dev/null)
if [[ -z "$VAULT_TOKEN" ]]; then
    echo "VAULT_TOKEN nem elérhető — állj meg"
    exit 1
fi

# Vault elérhetőség ellenőrzése
vault status 2>/dev/null || echo "Vault nem elérhető"
```

Ha Vault nem elérhető: rögzítsd és állj meg — ne próbálj továbblépni.

## Elvégzendő lépések

```bash
cd ${CIC_RELAY_PATH}
export VAULT_TOKEN=$(cat ${XDG_RUNTIME_DIR}/vault/sign-token)
COMPOSE_FILE=docker-compose.yaml make build-relay
```

`make build-relay` pipeline: `fetch-pki → prepare → quality → test-go → coverage → binary build`

## Output fájlok

`output/full-build-report.md`:

```markdown
## Vault előkészítés
**VAULT_TOKEN elérhető:** igen / nem
**Vault status:** [vault status kimenet]

## make build-relay
**Exit code:** 0 / 1
**fetch-pki:** sikeres / sikertelen
**quality gate:** sikeres / sikertelen
**test-go:** sikeres / sikertelen
**Bináris:** [path + méret + sha256]

## Bináris verifikáció
**PKI cert embedálva:** igen / nem
**make manifest-src:** [kimenet]
```

`output/claim-evidence.md` — Kötelező tábla:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Vault token elérhető | true/false | token fájl olvasható | cat + test -n | kritikus |
| fetch-pki sikeres | true/false | exit code + PEM fájl | make fetch-pki futtatva | kritikus |
| make build-relay átmegy | true/false | exit code + bináris path | make build-relay futtatva | kritikus |
| bináris PKI certtel épül | true/false | strings relay \| grep -c "BEGIN CERT" | bináris inspect | közepes |

## Szabályok

- **Exit code 0 ≠ sikeres** — ellenőrizd a bináris méretét és a PKI embed meglétét
- Ha fetch-pki sikertelen: ne folytasd — rögzítsd a Vault hibát
- A keletkező bináris ne kerüljön git-be
