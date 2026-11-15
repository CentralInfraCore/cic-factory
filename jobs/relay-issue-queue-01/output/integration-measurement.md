# Integrációs regressziós mérés (#190) a mergelt `main`-en

Alap: `CentralInfraCore/CIC_Relay` `main@e43f2a826ca2adee717a0a7ae18ca220016fb7c1`, tree `6b9cc314e759e3485a7d278c52de2cc6a5a8e928`; a teszt blobja (`cmd/relay/hardening_integration_test.go`) `5690d615def1841cc687b7b2f52ff3423ea48acc`. A nyolc mergelt PR: #173 `9629baf`, #176 `e6d7616`, #182 `156cc81`, #180 `07bbce8`, #177 `676f79c`, #179 `8faf00c`, #181 `c5ae320`, #190 `e43f2a8`.

A mérés kötése: `evidence/integration-regression/PROVENANCE.txt`; a nyers kimenetek ugyanott (`00-baseline.txt`, `M01…M13`, `summary.json`, `mutations.json`). A futás `golang:1.26.11` Dockerben, `--network none` mellett történt (hálózat nélkül), a mergelt fa exportján.

## Mit fed le

A teszt a hat védelmet és a #181 határ-autorizációt együtt, a valódi belépési pontokon vizsgálja: prod indulás-deklarációk és CRL, ágyazott és telepített komponens-út, autorizáció + proof + egyidejű recorder, egress (kliens-izolációval: nem loopback tárcsázás elutasított és számolt).

## Mérés: alap + 13 mutációs ellenpróba

Szabály: az alapnak át kell mennie; mutációnként a megnevezett tesztnek **buknia** kell.

| Futás | Mutált fájl | Eredmény |
|---|---|---|
| 00-baseline | — | PASS |
| M01-recorder-lock-161 | `core/nexus/recorder/recorder.go` | FAILS as required (2 failing tests) |
| M02-trust-mode-default-159 | `cmd/relay/pki_bootstrap.go` | FAILS as required (2 failing tests) |
| M03-crl-signature-164 | `core/cabinet/pki_verify.go` | FAILS as required (2 failing tests) |
| M04-crl-freshness-164 | `core/cabinet/pki_verify.go` | FAILS as required (2 failing tests) |
| M05-crl-issuer-policy-164 | `cmd/relay/pki_crl.go` | FAILS as required (3 failing tests) |
| M06-shared-trust-context-166 | `cmd/relay/bootstrap.go` | FAILS as required (2 failing tests) |
| M07-evidence-required-165 | `core/cabinet/service.go` | FAILS as required (2 failing tests) |
| M08-egress-dial-guard-163 | `cmd/relay/egress_client.go` | FAILS as required (3 failing tests) |
| M09-egress-response-cap-163 | `cmd/relay/cic_flow_host_funcs.go` | FAILS as required (2 failing tests) |
| M10-boundary-authorization-157 | `core/cabinet/service.go` | FAILS as required (2 failing tests) |
| M11-input-validation-157 | `core/modules/schemacompile/validate.go` | FAILS as required (2 failing tests) |
| M12-api-token-check-157 | `cmd/relay/api_auth.go` | FAILS as required (2 failing tests) |
| M13-redirect-following-163 | `cmd/relay/egress_client.go` | FAILS as required (6 failing tests) |

Mind a 13 mutáció megbuktatja a tesztet (nyers kimenet a megfelelő `M..txt`-ben), az eredeti fájlok visszaállítása ellenőrzött.

## Amit a mérés NEM bizonyít

- Nem éles Vault: a recorder `Sign` hívása teszt-implementáció.
- Egy gyökér, nincs köztes CA; a CRL-policy `all` ága összetett láncokon nem mért (#189).
- Nincs valódi ágyazott modul; az ágyazott út szintetikus modulokkal mért (#188).
- Nincs folyamat-újraindítás és futásidejű CRL-elavulás (#189).
- A Rust `http-executor` paritás a #180 saját futásában mért (29/29), nem ebben.
- Egy korábbi, egyszeri mérés (tree `3d82b63b…` == `main@8faf00c`) nyers kimenete nem lett elmentve; ez a futás váltja ki, arra nem hivatkozom bizonyítékként.
- **Nem production-jóváhagyás:** a #155 és a #162 rendezéséig HOLD.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Az alap a mergelt `e43f2a8` fán zöld | verified | `evidence/integration-regression/00-baseline.txt`, `summary.json` | Docker, `--network none` | alacsony |
| Mind a 13 védelem-eltávolítás megbuktatja a tesztet | verified | `M01…M13` nyers kimenet, `mutations.json` | Mutációs futás a mergelt fa exportján | közepes: a mutáció egy-soros emuláció, nem valós regresszió |
| A mérés a megnevezett commithoz/tree-hez kötött | verified | `PROVENANCE.txt` (`git rev-parse` értékek) | Azonosítók újraszámolása | alacsony |
| A teszt nem érint valódi infrastruktúrát | verified | `--network none`; `isolatedEgressClient` elutasít és számol | A futás hálózat nélkül zöld | alacsony |
| Production biztonsági jóváhagyás | **nem** | #155 és #162 nyitva | — | — |
