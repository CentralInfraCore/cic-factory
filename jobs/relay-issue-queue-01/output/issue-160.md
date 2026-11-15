# #160 — nightly `security=failure` (diagnózis)

Alap: `CentralInfraCore/CIC_Relay`, default ág `main` (`gh repo view` igazolja), friss klón HEAD `852594ae6180828dac090038cc443a6ac3e57bd4`.

## Mit találtam

- A bukó futás: `42983215543` (2026-11-11, `schedule`, commit `13b8425`). A `security` job bukó lépése: **`Go vulnerability scan (today's database)`** (`govulncheck ./...`, kilépési kód 3). A `go` és `rust` job `skipped`, mert a `security` bukott.
- Ok: **GO-2026-6859**, Go standard library, `net/http`. Érintett: `go1.26.10`, javítva: `go1.26.11`. A govulncheck "Your code is affected by 1 vulnerability from the Go standard library"-t jelez; nincs más sérülékenység a függőségek között. A hívási út a `net/http`-be a relay saját kódjából indul (pl. `core/nexus/iac/source_upstream.go:100-119`, `cmd/relay/main.go:45,192`).
- A `13b8425` commitban a toolchain `go1.26.10` volt (`go.mod`, a `nightly.yml` `go-version: "1.26.10"` két helyen). Ez a futás logjában is látszik: `Successfully set up Go version 1.26.10`.
- Az ok tehát **függőség-szintű (toolchain-verzió)**, nem a relay kódja.
- A 2026-11-10-i nightly még zöld volt: a GO-2026-6859 a két futás között került az adatbázisba.

## Mi változott

**Semmi nem változott ebben a jobban: a javítás már a `main`-en van.** A `bc2c4e0` ("build: update the Go toolchain to 1.26.11 (GO-2026-6859) in every pin", #168) a `go.mod` toolchain sorát és a workflow-pineket 1.26.11-re emelte. A #160 issue-nak az utolsó nightly futása (2026-11-14, `43572627224`) még a `13b8425`-ön futott, a #168 előtt; azóta nem volt nightly futás.

Nem nyúltam workflow-fájlhoz (input.md szabály), és nincs PR ehhez az issue-hoz.

## Hívási út / reachability

Nem új védelem, nincs kódváltozás: a `go.mod` `toolchain go1.26.11` sora (`go.mod:5`) a javítás hordozója.

## Nyitott kérdések

- A nightly zöld állapotát csak egy új `schedule` futás igazolja a `main` új fején; ezt ez a job nem tudja előállítani (CI nem kapu). A lezárás (`Closes`) a tulajdonosé.
- Az issue-t a nightly-failure workflow addig "Failed again"-nel kommentezi, amíg nem zöld a futás; a lezárás kézi.

## Claim-evidence

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A bukó lépés a `Go vulnerability scan (today's database)` | verified | `gh run view 42983215543 --json jobs`: `security` / `Go vulnerability scan (today's database)` = failure | Futás-metaadat és job-log olvasása | alacsony |
| Az ok GO-2026-6859 (`net/http`, fixed in go1.26.11), az egyetlen találat | verified | Job-log: "Vulnerability #1: GO-2026-6859 … Found in net/http@go1.26.10, Fixed in net/http@go1.26.11"; "found no other vulnerabilities" | A `gh api …/actions/jobs/130398242111/logs` kimenet olvasása | alacsony |
| A bukó commit Go 1.26.10-et használt | verified | `git show 13b8425:go.mod` → `toolchain go1.26.10`; `nightly.yml:55,179` → `1.26.10`; log: "Successfully set up Go version 1.26.10" | `git show` és logolvasás | alacsony |
| A `main`-en a javítás (1.26.11) már megvan | verified | `git log -S'1.26.11'` → `bc2c4e0` (#168); `go.mod:5` `toolchain go1.26.11` | git-történet és `go.mod` olvasása | alacsony |
| A `main` (852594a) govulncheck-tiszta Go 1.26.11 alatt | verified (helyi, nem CI) | `docker run golang:1.26.11 … govulncheck@v1.1.4 ./...` → "No vulnerabilities found.", EXIT=0 | Helyi futtatás ugyanazzal a govulncheck-verzióval, mint a workflow | közepes: az adatbázis napi, a CI-futás külön igazol |
| A nightly `security` job zöld a `main` új fején | verified (a lezáráskor) | nightly run 43692764730 a `main@676f79c`-n (2026-11-15): `security` = success, "Successfully set up Go version 1.26.11", "No vulnerabilities found."; az issue ezen az alapon lezárva | Actions-job és log olvasása | közepes: a teljes nightly többi jobja a lezáráskor még nem indult el |
