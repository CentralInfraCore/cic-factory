# Integrációs mérés a hat mergelt PR után

Alap: `CentralInfraCore/CIC_Relay` `main@8faf00c` (a #173, #176, #182, #180, #177, #179 mergelve). A mérést az `origin/feature/relay-164-crl-verification@720b2ad` fáján végeztem, amely tartalmazza a `main@676f79c`-t, így a fája megegyezik a #179 mergelése utáni `main`-nel. A #181 (`/v1/schema/compile` autorizáció) **nincs** benne: HOLD.

A mérés egy összetett forgatókönyv (`cmd/relay/hardening_integration_test.go`, **nincs commitolva, nincs PR**: egyszer futtatott mérés a scratchpadben; commitolása külön döntés), amely a hat PR hatását **együtt** vizsgálja a valódi belépési pontokon (`bootstrapTrust`, `loadModule`, `loadEmbeddedComponents`, `loadInstalledComponents`, `Setx`, `/set` handler, `newCICFlowRegistry`).

## Mit fed le

1. **Prod bootstrap + PKI + CRL + komponensek:** operátor-CA + CRL a bundle-ben, `CIC_TRUST_MODE=prod`, `CIC_CRL_REQUIRED_ISSUERS=<a gyökér ujjlenyomata>`. Három modul mindkét betöltési úton (ágyazott és telepített), ugyanazzal a trust contexttel:
   - az operátor CA-ja által aláírt, nem visszavont: mindkét úton betöltődik, megkapja a capability-t;
   - az operátor CA-ja által aláírt, **a CRL-ben visszavont**: mindkét úton elutasított, nincs capability;
   - a bundle-n kívüli CA által aláírt: mindkét úton elutasított, nincs capability.
   Az indulás deklarációi: hiányzó `CIC_TRUST_MODE`, hiányzó prod CRL-policy és egy a bundle-ben nem szereplő követelt kibocsátó mind indulási hiba.
2. **Proof persistence + evidence:** valódi `GitStateRecorder` + `WorkflowRecorder`, `CIC_EVIDENCE_REQUIRED`-nek megfelelő beállítás, a `/set` handleren át: egészséges recorderrel `proof.persisted=true` és a visszaadott commit megegyezik az audit repó HEAD-jével, a lánc `VerifyChain`-nel ellenőrizhető; recorder-hibánál 503 `evidence_required`, `execution_completed=true`, `proof.persisted=false`, `chain_hash`, a recorder hibaszövege nem jut el a hívóhoz.
3. **Egress:** az éles alapértelmezett doer (`newCICFlowRegistry(nil, nil)`, pontosan amit a `main` köt be) nem tárcsáz engedélyezett, de privát célt (`blocked_address`), a szerver el sem érhető.

## Eredmény

| Mérés | Eredmény |
|---|---|
| Összetett forgatókönyv (3 rész, 7 eset) | mind átment |
| Teljes csomagfuttatás (`go test ./...`) | 26/26 csomag `ok` |
| `go test -race` (cmd/relay, cabinet, recorder, schemacompile) | mind `ok` |
| `go vet ./...` | üres |
| `staticcheck` (cmd/relay, cabinet, recorder, schemacompile) | rc=0 |
| `deadcode` a védelmek szimbólumaira | egyik sem halott: mind elérhető az éles útról |
| `MANIFEST.sha256` | "no drift" |
| `gofmt` | a mérési teszt-fájl formázatlan (nem commitolt); minden commitolt fájl tiszta |

## Amit a mérés NEM bizonyít

- **Nem teljes a hét PR:** a #181 (compile-végpont autorizáció) nincs benne, így a `/v1/schema/compile` és a `/set` közti megkerülés (a review F1) nyitva marad. A #181 mergelése után az érintett integrációs teszteket ismételni kell.
- **Nem éles Vault:** a recorder `Sign` hívása teszt-implementáció, a Vault-aláírás ellenőrzés valódi Vault ellen nem futott.
- **Egy gyökér, nincs köztes CA:** a forgatókönyv egyetlen gyökér CA-ra épül; köztes CA-val és több kibocsátóval a CRL-policy `all` ága összetett láncokon nem mért.
- **Nincs valódi ágyazott modul:** az ágyazott fában nincs modul; az ágyazott út szintetikus modulokkal mért (#188).
- **Nincs folyamat-újraindítás és futásidejű CRL-elavulás:** a CRL-ek indításkor töltődnek (#189).
- **A Rust oldal nem része ennek a futásnak:** a `http-executor` paritás-tesztje a #180 saját futásában (29/29, fmt, clippy `--no-default-features`) mért, nem ebben.
- **Nem production-jóváhagyás:** a #155 (privát kezelés) és a #162 (signing szerződés) rendezéséig a produkciós biztonsági jóváhagyás HOLD. A hat issue lezárása fejlesztési mérföldkő.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A hat PR együtt működik a prod bootstrap, PKI, CRL és mindkét betöltési út mentén | verified | `TestHardeningIntegration_ProdBootstrapPKICRLComponents` (4 al-eset) az `origin/...@720b2ad` fáján | Összetett teszt a valódi belépési pontokon | közepes: szintetikus modulok, egy gyökér |
| A visszavont tanúsítvány a CRL miatt utasított el (nem más ok) | verified | az azonos gyökérrel aláírt másik levél betöltődik, a visszavont nem | Kontroll-eset ugyanabban a tesztben | alacsony |
| A proof persistence és az evidence-mód együtt működik a valódi git recorderrel | verified | `TestHardeningIntegration_ProofPersistenceAndEvidence`; commit == audit HEAD, `VerifyChain` ok | Összetett teszt a `/set` handleren át | közepes: teszt-Vault |
| Az éles alapértelmezett doer nem éri el a privát célt | verified | `TestHardeningIntegration_EgressDefaultClient`; a szerver 0 találat | Összetett teszt | alacsony |
| A teljes csomag zöld a mergelt állapoton | verified | 26/26 `ok`, `-race` ok, vet/staticcheck tiszta | Helyi futás Dockerben | alacsony |
| A #181 hatása a mérésben | **nem mért** | A #181 nincs a fában (HOLD) | — | magas |
| A mérés production-jóváhagyás | **nem** | #155 és #162 nyitva | — | — |
