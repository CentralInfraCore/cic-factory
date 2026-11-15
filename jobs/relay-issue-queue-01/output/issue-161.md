# #161 — recorder `signAndCommit` szerializálás

Alap: `CIC_Relay` `main@852594a`. Ág: `feature/relay-161-recorder-serialize`, helyi commit `0a6f7ac` (pusholva, PR: https://github.com/CentralInfraCore/CIC_Relay/pull/173, base `main`).

## Mit találtam a kódban (állítás-ellenőrzés az issue szövegével szemben)

- Az issue a `13b8425`-re hivatkozik, a kód a `852594a`-n azonos módon viselkedik. A `core/nexus/recorder/recorder.go` `signAndCommit` függvényében nem volt zár; a HEAD-olvasás (`getHeadHash`), a manifest aláírása, a négy fix nevű fájl írása, a `git add .` és a `git commit` egymás után, védelem nélkül futott.
- A `getHeadHash` hibáját a kód elnyelte és `parent = ""`-lal aláírt (`recorder.go` régi 172–175. sor). Ez az issue 4. pontja, igaz.
- Az issue 1–3. esete (azonos szülő, kevert fájlok, `index.lock`) **futtatással is igazolt**: a javítás nélküli kódon a párhuzamos teszt `git add . failed … index.lock: File exists` hibával bukik (`161-without-fix-summary.txt`). Az 1. (hamis `chain broken`) és a 2. (kevert fájlok) esetet külön nem váltottam ki; azt az `index.lock` ütközés eltakarja.
- Az issue állítása, hogy a `Setx` párhuzamosan hívható, olvasat: a HTTP handler útját nem követtem végig. A hívási út a recorderig megvan (lásd lent).

## Mi változott

- `GitStateRecorder` kapott egy `sync.Mutex`-et; a `signAndCommit` a HEAD-olvasástól a commit végéig tartja. Egy folyamatra elég. Több író esetén fájlzár kellene (nem ennek a PR-nak a tárgya).
- A HEAD-olvasási hiba most hibaként tér vissza (`failed to read the parent commit`), nem ír üres szülőt.
- Teszt: `recorder_concurrency_test.go` (új), egy meglévő eset (`git command fails`) átírva: a `.git` törlése már a szülő-olvasásnál bukik, ezért az eset most sérült indexszel hibáztatja a `git add`-ot.
- A zár a Vault `Sign` hívás alatt is tart (az aláírt szülő miatt kötelező): az írások sorosak, ez áteresztőképesség-ár.

## Hívási út (production, `file:line`)

`cmd/relay/main.go:480` `NewWorkflowRecorder(gitRecorder)` → `main.go:486` `cabinet.WithRecorder(wr)` → `core/nexus/recorder/workflow_recorder.go:37` `RecordState` → `core/nexus/recorder/recorder.go:98` → `signAndCommit` (`recorder.go:161`). További production hívók: `core/nexus/operator/bootstrap.go:107`, `core/nexus/operator/lifecycle.go:130`, `tools/statechain-demo/main.go:73,92,95`. `deadcode ./...` kimenetében nincs `recorder` találat.

## "Javítás nélkül bukik" bizonyíték

A `recorder.go`-t ideiglenesen `git checkout`-tal visszaállítottam, az új teszteket lefuttattam:

```
--- FAIL: TestSignAndCommit_ConcurrentRecordsKeepChainVerifiable
--- FAIL: TestSignAndCommit_HeadReadFailureIsAnError
FAIL	centralrelay/core/nexus/recorder
```

Helye: scratchpad `161-without-fix-summary.txt`. A javítás visszaállítva, a futás utáni állapot zöld.

## Helyi kapuk (Docker `golang:1.26.11`, a CI nem kapu)

- `gofmt -s -l`: üres; `go vet ./...`: üres; `staticcheck ./core/nexus/recorder/`: rc=0.
- `go test -race -count=1 ./core/nexus/recorder/`: `ok`; `go test -count=1 ./...`: minden csomag `ok`.
- A Rust/FFI/live-Vault kapuk nem érintettek (csak Go-csomag változott).

## Külső review (PR #173, 0a6f7ac) kezelése

A review három észrevételét a kódhoz és a GitHubhoz mérve kezeltem:

- **CI-állapot:** a review "verify folyamatban" állítása elavult; a `0a6f7ac` HEAD-en a `gh pr view` szerint minden check `SUCCESS` (verify, coverage, go, rust, ffi, mutation-pr, manifest, completeness), a PR `MERGEABLE`.
- **P2 egyedi `run-id`:** igaz, a commitszám és a lánc nem igazolta, hogy minden rekord megmaradt. A teszt most mind a 12 `run-id`-t pontosan egyszer várja, és minden commit `meta.json`-ja a commit-üzenet `run-id`-jét hordozza. Javítás nélkül ez a hiányzó `run-id`-ket jelzi (scratchpad `161b-without-fix.txt`). Commit: `3c240c6`.
- **P2 példányszintű zár:** a korlát dokumentált volt; a zár fölötti kommentben most szerződésként áll ("egy recorder példány repónként"), fájlzár nem készült.
- **P3 context-tudatos várakozás:** **nem implementáltam**: a nulla értékű `GitStateRecorder{}` literálok (a tesztekben) egy csatorna-alapú zárat inicializálás nélkül örökre blokkolnának; ezért a várakozás szerződése a kommentben van (a várakozást az előző rekord Vault `Sign` hívása és a git parancsai korlátozzák).

## Nyitott kérdések / jelzések

- **Állapot:** a PR (#173) nyitva volt, a review-kiegészítésekkel (`3c240c6`) a jóváhagyott HEAD-en **mergelve** (`9629baf`, 2026-11-15), az issue lezárva.
- **Idegen módosítások a klónban**: a klónozás után 15 másodperccel 189 követett `.yaml` (companion-metaadat) fájl átíródott és 13 új jelent meg, nem az én parancsomra. A commitba explicit útvonalakkal csak a 3 saját fájl került. Az átíró eszköz azonosítatlan.
- A commitot egy globális hook a fejlesztői kulccsal (`cic-my-sign-key`) Vault-aláírta; a szerző a helyi git-identitás.
- A kapcsolódó "recording failure nem jut el a hívóhoz" pont (#165) külön issue, itt nem érintettem.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `signAndCommit` nem volt szerializálva | verified | `recorder.go` régi állapota: nincs zár; javítás nélkül a párhuzamos teszt `index.lock` hibával bukik | Kód olvasása + a javítás visszavonásával futtatott teszt | alacsony |
| A HEAD-olvasási hiba üres szülővel aláírt | verified | Régi `recorder.go:172-175`; a `HeadReadFailureIsAnError` teszt javítás nélkül bukik | Kód olvasása + a javítás visszavonásával futtatott teszt | alacsony |
| A zár védi a szülő-olvasástól a commitig tartó szakaszt | verified | `go test -race` zöld, N=12 párhuzamos rekordra pontosan N+1 commit és `VerifyChain` ok | Helyi teszt | közepes: egy folyamatra érvényes, több író fájlzárat kívánna |
| A `Setx` HTTP-ről párhuzamosan hívható | **nem igazolt** | Az issue olvasata; a handler utat nem követtem végig | — | közepes |
| A PR mergelve van | verified | https://github.com/CentralInfraCore/CIC_Relay/pull/173, merge-commit `9629baf` | `gh pr view` | alacsony |
