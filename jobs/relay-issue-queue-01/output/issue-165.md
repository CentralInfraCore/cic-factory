# #165 — `Setx` `proof.persisted` + "evidence required" mód

Alap: `CIC_Relay` `main@852594a`. Ág: `feature/relay-165-proof-persisted`, commitok `4137626` és `deff69b` (pusholva, PR: https://github.com/CentralInfraCore/CIC_Relay/pull/177, base `main`).

## Mit találtam a kódban (állítás-ellenőrzés az issue szövegével szemben)

- **Igaz:** a `core/cabinet/service.go` `Setx` rögzítési blokkja hibánál csak logolt, és `Warnings: nil`-lel normális választ adott (régi `service.go:298-312`). A hívó nem tudta megkülönböztetni a "lefutott" és a "rögzült" állapotot.
- **Igaz:** a rögzítő nil (Vault nélkül `buildRecorderOption` → `WithRecorder(nil)`, `main.go`) esetén ugyanígy néma volt a hiány.
- **Az issue nem említi, de a kódban így van:** az `ExecutionRecorder.Record` csak `error`-t ad, és a `WorkflowRecorder` eldobta a `RecordState` commit hash-ét (régi `workflow_recorder.go:37`). Az issue "a commit hash visszaadva" acceptance pontjához ezért interfész-bővítés kellett; a régi interfész változatlan maradt, mellé új opcionális `CommitRecorder` került.
- A `Setx` válasza JSON-ban címkék nélküli mezőkkel megy ki (`Results`, `Warnings`, `Trace`); az új mező az issue szövegéhez igazodva `json:"proof"` (kisbetűs), így a kulcsstílus a válaszban vegyes. Ezt a PR jelzi.

## Mi változott

- `SetResponse.Proof` (`persisted`, `commit`, `error_code`) minden sikeres végrehajtáskor visszajön; az `error_code` rögzített érték (`record_failed`, `recorder_not_configured`), a recorder hibaszövege (Vault-útvonal, token) csak a logba kerül.
- `cabinet.WithEvidenceRequired(bool)` + üzemeltetői oldalon `CIC_EVIDENCE_REQUIRED` (csak `true`/`false`, más érték indulási hiba, hogy egy elírás ne kapcsolhassa ki a kötelező módot).
- Kötelező módban a nem rögzült bizonyíték (rögzítési hiba **vagy** nincs recorder) `ErrEvidenceRequired`; a handler **HTTP 503 `evidence_required`**-re képezi. A workflow ekkor már lefutott, ezért a hibaüzenet tartalmazza a `chain_hash`-t (részleges bizonyíték nem vész el).
- Alapértelmezés: HTTP 200, `proof.persisted=false`, a trace megmarad.
- `WorkflowRecorder.RecordCommit` a commit hash-t visszaadja; `Record` erre épül. `context/SYMBOLS.md` újragenerálva (6 új exportált szimbólum: szerződés-diff).

## Hívási út (production, `file:line`)

HTTP: `cmd/relay/main.go` `setHandler` → `cabinet.NewAPI(s.api).Set` (`core/cabinet/api_set.go`) → `Setx` → `recordProof` (`core/cabinet/service.go`) → `WorkflowRecorder.RecordCommit` (`core/nexus/recorder/workflow_recorder.go`) → `GitStateRecorder.RecordState`. A kapcsoló: `main.go` `evidenceRequiredFromEnv` → `cabinet.WithEvidenceRequired(...)` a `NewCabinetService` hívásban. `deadcode ./...`: nincs találat az új függvényekre.

## "Javítás nélkül bukik" bizonyíték

A régi viselkedés az új típusok alatt visszaállítva (scratchpad `165-without-fix-summary.txt`): a 7 cabinet-teszt (`TestSetx_Proof_*` mind) és `TestSetHandler_EvidenceRequired` bukik. **Nem bukik** (karakterizáló, nem védelem-bizonyíték): `TestSetHandler_ProofInResponse` (a mock válaszát szerializálja), `TestEvidenceRequiredFromEnv` (új függvény), a `RecordCommit` tesztek (a `RecordCommit` nem lett visszavonva; a `var _ cabinet.CommitRecorder` fordítási ellenőrzés viszont a metódus törlésekor bukik).

## Helyi kapuk (Docker `golang:1.26.11`)

`gofmt -s -l` üres; `go vet ./...` üres; `staticcheck` (cabinet, recorder, cmd/relay) rc=0; `go test -count=1 ./...` minden csomag `ok`; `symbolsgen` lefuttatva, a diff a commitban.

## Külső review (PR #177, 4137626) kezelése

- **CI-blokkoló: igaz, saját hiba.** A `manifest-check` a GitHub Actions logja szerint azért bukott, mert a `context/SYMBOLS.md` hash-e eltért a `MANIFEST.sha256`-ban lévőtől. A `symbolsgen` újragenerálta a fájlt, a manifestet viszont nem frissítettem, és a helyi kapusorban nem szerepelt a `scripts/gen_manifest.sh`-val előállított manifest összevetése. Javítva: a manifest újragenerálva (a `main`-hez képest csak a `SYMBOLS.md` sora változik), és a CI lépésével azonos `diff` helyben "no drift". A #173 és #176 nem érintett, mert ott nem változott a `SYMBOLS.md`.
- **API-szemantika: elfogadva, megvalósítva.** A kötelező-evidence 503 a workflow lefutása után jön, tehát a kliens nem kezelheti vakon újrapróbálható hibaként. A hiba most strukturált (`cabinet.EvidenceRequiredError`: workflow, chain hash, hibakód), a 503 törzse `execution_completed=true`, `proof.persisted=false` és `chain_hash` mezőt ad a szokásos `code`/`error` mellett. A régi szöveges válasszal a két új handler-teszt bukik (scratchpad `165b-without-fix.txt`). Commit: `deff69b`.

## Nyitott kérdések / jelzések

- **Docs:** a `docs/{hu,en}/pipeline/relay-container.md` env-táblájába a `CIC_EVIDENCE_REQUIRED` sort szándékosan nem vettem fel: a szomszédos `CIC_TRUST_MODE` sort a #176 módosítja, a két PR merge-konfliktusba futna. Follow-up a két merge után.
- **Kötelező módban a workflow mellékhatása már megtörtént** a 503 előtt; a 503 ezt nem vonja vissza. Ez a mód szemantikája, nem hiba: a hívó a chain hash-sel tudja utólag kezelni.
- **Nem tettem:** indulási hiba, ha `CIC_EVIDENCE_REQUIRED=true` és nincs recorder (jelenleg hívásonként 503). Az issue nem kéri; ha kell, külön döntés.
- **Workflow-szintű deklaráció** ("a workflow vagy a deployment") nem készült: csak üzemeltetői szint, mert a workflow-formátum bővítése szerződésváltozás volna.
- A #161 (recorder szerializálás, PR #173) független fájlokat érint, nincs ütközés.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A rögzítési hiba csendben maradt a válaszban | verified | Régi `service.go:298-312`; `TestSetx_Proof_RecorderOutage_NotRequired_ReportsNotPersisted` javítás nélkül bukik | Kódolvasás + a régi viselkedéssel futtatott teszt | alacsony |
| Egészséges recorder → `persisted=true` + commit hash | verified | `TestSetx_Proof_RecorderHealthy_PersistedWithCommit`; `TestWorkflowRecorder_RecordCommit_RealGitRecorder_ReturnsHead` a valódi git HEAD-del | Teszt (a javítás nélkül bukik / valódi recorder) | alacsony |
| Kötelező módban a hiba explicit, nem sima siker | verified | `TestSetx_Proof_RecorderOutage_Required_Fails`, `TestSetHandler_EvidenceRequired` (javítás nélkül buknak) | Teszt | közepes: a `main()` kapcsoló-bekötése nincs futtatva |
| A recorder hibaszövege nem szivárog a válaszba | verified | A tesztben "vault"/"secret/ci-token" nincs a JSON-ban és a hibában | Teszt | alacsony |
| A kapcsoló az éles úton bekötött | verified (olvasat) | `main.go` `evidenceRequiredFromEnv` → `WithEvidenceRequired` a `NewCabinetService` hívásban | Kódolvasás + `deadcode` | közepes: `main()` maga nem futott |
| Workflow-szintű "evidence required" deklaráció | **nem készült** | Csak üzemeltetői szint; a workflow-formátum szerződésváltozás | — | közepes |
| A PR nyitva van | verified | https://github.com/CentralInfraCore/CIC_Relay/pull/177 | `gh pr create` kimenet | alacsony |
