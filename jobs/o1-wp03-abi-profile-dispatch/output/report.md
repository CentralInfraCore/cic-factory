# o1-wp03-abi-profile-dispatch: jelentés (ABI-profil betöltő és profil-alapú dispatch)

**Készítő:** az orchestrátor (a végrehajtó agent az első körben a tele `/tmp` miatt BLOCKED lett; a második folyamat megszakadt; a munkát az orchestrátor fejezte be). **Minden szám a saját docker-futásokból való**, a naplók az `output/evidence/` alatt.

## Rögzített bemenetek és eredmény

| Elem | Érték |
|---|---|
| CIC_Relay alap | `86ea1ab30e1f234ab294e51385f6f51bbff0aff9` (`main`) |
| Draft PR | **https://github.com/CentralInfraCore/CIC_Relay/pull/234** (`--base main`) |
| Commitok | `7b0e2f7` (megvalósítás), **`c9603c7`** (a külső review F1–F5 javításai) |
| Commit-aláírás | a gyári hookon át, fejlesztői kulcs; nem release-aláírás |
| Környezet | docker `golang:1.26.11` (`sha256:957952ae…`); a Go-eszközlánc a gépen nem natív |
| **GitHub CI a `c9603c7` head SHA-n** | **UNVERIFIED / folyamatban:** az ellenőrzéskor 8 job `pass`, 3 `pending` (`go (chunk 0)`, `object-evidence`, `rust`), 1 `skipping` (rust shard). A végleges eredményt a head SHA-ra újra le kell kérdezni. (A korábbi, zöld CI a `7b0e2f7`-re vonatkozott, nem erre.) |
| Evidence-naplók | a helyi futások a munkafán készültek, amely a `7b0e2f7`-re épülve lett a `c9603c7` |

## Mit valósít meg

`ParseProfile` (strict wire-olvasó: ismeretlen, kis/nagybetűben eltérő és duplikált kulcs, hiányzó kötelező kulcs, záró adat, nem pozitív limit, duplikált host-képesség elutasítva), `ProfileDigest` (a nyers bájtok sha256-ja, ABI-05), `ProfileSignedBytes` (`CICABIPROFv1`), `CheckProfileSemantics` (ABI-01–04, SS-05; a referencia `check_profile_semantics` portja, mind a 10 eset teszt), `ResolveEffect` (fail-closed `external-write`), `ProfileRegistry.Admit` (operátori pin, aláírás-varrat, szemantika; hiányzó verifier vagy schema-tár fail-closed hiba), `ModuleProfileBinding` (manifest-pin, op-halmaz, hitelesített envelope-digest kötelező, a profil változtathatatlan másolata; külön érték, a `ModuleDescriptor` és a `Checksum()` változatlan), és a `Setx` profil-alapú útja (`WithGenericDispatch`, alapértelmezetten **ki**, `CIC_ABI_GENERIC_DISPATCH` csak pontosan `true`/`false`). A `sign+send` operáció fail-closed (WP-04 hatáskör). A mock verifier csak tesztfájlban él.

## Acceptance

Státusz: komponensszintű, a helyi docker-futás alapján; a GitHub CI a `c9603c7`-re függőben.

| AC | Státusz | Bizonyíték |
|---|---|---|
| AC-03-1 második, szintetikus profil befogadható Relay-kód változtatása nélkül | PASS | `TestAC03_1_SecondSyntheticProfileAdmittedByConfigurationOnly` |
| AC-03-2 ismeretlen/nem befogadott `profile_digest`, extra manifest-op elutasított a megnevezett kóddal | PASS | `TestAC03_2_*`; M08, M09, M11, M12 |
| AC-03-3 ABI-01…04 és a limit minden hibakódja tesztelt (10 referencia-eset) | PASS | `TestAC03_3_ProfileSemanticsReferenceCases`; M01–M07 |
| AC-03-4 a legacy négy op viselkedése változatlan | PASS | `TestLegacyModuleUnaffectedWhenSwitchIsOn`, a meglévő tesztek zöldek; az explicit legacy modul nem érintett |
| AC-03-5 az új dispatch alapértelmezetten ki van kapcsolva, kapcsoló + reachability | PASS | `TestAC03_5_*`, `TestGenericDispatchFromEnv`; M13, M20; lásd reachability |
| AC-03-6 minden negatív teszt a megnevezett okból bukik | PASS | **30 bevetett hiba, mind a megnevezett teszten bukott** (`fault-injection.txt`); a baseline előtte és utána zöld |

Review-javítások (külső review, `c9603c7`): F1 pontos operation-azonosság a profil-úton (M21); F2 elavult kötés vagy profilt igénylő, de be nem kötött modul elutasítva, nincs legacy fallback (M14, M22); F3 envelope-digest kötelező és profil-snapshot (M23, M24); F4 strict wire-olvasó (M25–M29); F5 mock tesztfájlban, hiányzó verifier/tár fail-closed (M30). F6 integrációs függőség (alább).

## Kapuk (helyi)

`go test ./... -count=1`: minden csomag ok; `-race` a `core/cabinet` és `cmd/relay` csomagon ok; lefedettség `core/cabinet` 94,0%, `cmd/relay` 91,2%; `gofmt -l` üres; `go vet ./...`, `staticcheck v0.6.1` tiszta; docgate (Go-rész) 126 fájl, 0 hiányzó; a `SYMBOLS.md` és a `MANIFEST.sha256` újragenerálva; a companion yaml-ok (`tools/go.meta.gen.py --parser ast --merge`) frissítve.

## Reachability

A `deadcode v0.44.0` az alap (`86ea1ab`) és az új állapot különbségén: az új, **production-ból elérhetetlen** szimbólumok a betöltő, az admission, a binding és a szemantika (`ParseProfile`, `CheckProfileSemantics`, `ProfileRegistry.Admit`, `NewModuleProfileBinding`, `WithModuleProfileBindings`, …): **scaffold**, mert a produkciós kód még nem regisztrál kötést. A kapcsoló és a `Setx` profil-útja (`profileBindingFor`, `WithGenericDispatch`, `CicWasmHost.Call`) **elérhető, de inert**: nincs regisztrált kötés, ezért bekapcsolva sincs hatása (a `main` ezt figyelmeztetéssel naplózza).

## Claim-evidence

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat | Szint |
|---|---|---|---|---|---|
| a profil-betöltő és a szemantikai szabályok a referencia szerint működnek | implemented (komponens) | 10 referencia-eset, 30 bevetett hiba | teszt + bevetett hiba | nincs production-hívó | komponens |
| az új dispatch alapból ki van kapcsolva | implemented | AC-03-5, M13, M20 | teszt + bevetett hiba | — | komponens |
| a profil-aláírás ellenőrzése | **scaffold (mock)** | `ProfileSignatureVerifier` interfész, mock csak tesztben | — | a valódi ellenőrzés a WP-02 trust bundle-jére vár | provizórikus |
| a binding a #233 hitelesített envelope-identitásához kötött | scaffold | az `EnvelopeDigest` mező kötelező, a forrása még nincs bekötve | — | az integráció a két PR közös ágán derül ki | integráció: nem mért |
| a sign+send operáció végrehajtása | concept (WP-04) | fail-closed teszt | — | — | — |

## Mért / nem mért / nyitott

**Nem mért (UNVERIFIED):** a GitHub CI a `c9603c7`-en (függőben); production-integrációs bizonyíték (nincs production-hívó); a valódi profilaláírás-ellenőrzés; a kötés és a #233 envelope-identitás tényleges összekötése.

**Nyitott (F6, integráció):** a tényleges request/response schema-validáció; az effect-resolution production-döntésbe kötése; a `local` operáció host-képesség-mentességének bizonyítása; a profil-limitek runtime-kikényszerítése. Ezek a WP-03/WP-04 integrációs acceptance részei.

**Menet közbeni hiba, rögzítve:** egy megszakított mutációs futás a forrásban hagyott egy mutációt; észleltem és visszaállítottam, a végső forrásban nincs maradvány (`grep 'if false'` 0 találat). Factory-szintű backlog: lásd `decisions/factory-backlog-mutation-isolation.md`.

**HOLD:** merge, valódi aláírás, countersign, release, production aktiválás.
