# relay-issue-queue-01 — CIC_Relay nyitott issue-k sorozatos feloldása

## Kontextus

A `CentralInfraCore/CIC_Relay` repón nyitott biztonsági és megbízhatósági issue-k vannak
(`gh issue list -R CentralInfraCore/CIC_Relay`). Ez a job a jóváhagyott sorrendben, **egy issue
= egy PR** elven halad végig rajtuk. Minden issue törzse tartalmaz `Proposal` és `Acceptance
(negative tests)` szakaszt: ez a definition of done. Az issue-k forrásalapú olvasatok
(`main@13b8425`, nem futtatással igazoltak), ezért **minden állítást a kódban ellenőrizz**, mielőtt
rá építesz.

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`, `limits`
   fogalmakra. Státuszt (implemented / scaffold / concept) node- vagy fájlszinten támassz alá.
2. Klónozd a `CIC_Relay` repót a workspace-be (friss klón; a helyi klónok elavultak). Rögzítsd az
   ágat és a commit-azonosítót. Az alapértelmezett ág `main`; a PR-ok base-e a repó default ága,
   ezt `gh repo view` kimenettel igazold, ne feltételezd.
3. Minden issue-t olvass végig a `gh issue view <n> -R CentralInfraCore/CIC_Relay` paranccsal,
   a megjegyzésekkel együtt.

## Sorrend

1. **#160** nightly `security=failure` — diagnózis: olvasd el a futás logját
   (`gh run view 42983215543 -R CentralInfraCore/CIC_Relay --log-failed`), nevezd meg a bukó
   lépést és az okát. Javítás csak ha az ok kód- vagy függőség-szintű; workflow-fájlhoz nem nyúlsz.
2. **#161** recorder `signAndCommit` szerializálás (mutex, `parent=""` hiba, párhuzamos teszt).
3. **#159** `CIC_TRUST_MODE` nincs default, `prod`-ban üres/betöltetlen trust store hiba.
4. **#166** embedded modulok a közös `pkiAssets`-en. Ha a döntés (embedded = konstrukciósan
   megbízott?) nem olvasható ki a kódból és a dokumentumokból: **állj meg és kérdezz**, ne dönts.
5. **#165** `Setx` `proof.persisted` + "evidence required" mód.
6. **#164** CRL aláírás és frissesség ellenőrzés (a #159 után).
7. **#163** `actuate` redirect/méretkorlát/policy parity a Rust `http-executor`-ral.
8. **#155** prod fail-closed modulbetöltés + `git.*` host függvények modulonkénti kapuzása
   (a host-függvény felsoroló teszt kötelező).
9. **#162** capability binding a modul/manifest hitelesítéséhez. A boríték-formátumnak a
   signing oldalon kell létezni: ha nem találod, **állj meg és jelezd**.
10. **#157** `/v1/schema/compile` auth + input validáció + route-osztályozó teszt.

**Nem ennek a jobnak a része:** #156 és #158 (CIC-Schemas formátum, illetve Vault-oldali kulcs
szükséges), #169 (CI-felzárkóztatás), #130, #101, #89, #26. Ne kezdd el őket.

## Források

- Tájékozódás (elavulhat): `${CIC_RELAY_PATH}`, `~/sync/git.partners/CentralInfraCore/CIC_Relay`;
  a munka a workspace-beli friss klónon megy.
- Kiinduló fájlok az issue-kból: `core/nexus/recorder/recorder.go`, `core/cabinet/service.go`,
  `core/cabinet/pki_verify.go`, `cmd/relay/bootstrap.go`, `cmd/relay/main.go`,
  `cmd/relay/cic_flow_host_funcs.go`, `cmd/relay/cic_flow_registry.go`.

## Tiltott rövidítések

- `fájl vagy szimbólum létezik` ≠ `implemented`; `teszt zöld` ≠ `a védelem él`.
- `exit code 0` ≠ sikeres: a kimenetet olvasd el.
- Az issue szövege nem bizonyíték: a kódban ellenőrzött állítás az.

## Szabályok

- **Egy issue = egy ág = egy PR** (`feature/relay-<issue>-<tárgy>`), a PR törzse hivatkozik az
  issue-ra (`Refs #N`, NEM `Closes`: a lezárás a tulajdonosé). Angol PR-cím és -törzs.
- **Negatív tesztek kötelezőek**: az issue összes Acceptance pontjához teszt, és minden új
  teszt **bukjon a javítás nélkül** — ezt futtasd le és rögzítsd (a javítás ideiglenes
  visszavonásával). Bukni nem tudó teszt nem bizonyíték.
- **Reachability**: új vagy módosított védelemről csak akkor mondd, hogy bekötött, ha a
  production hívási út megvan `file:line` formában (nem teszt-hívás). Parancs:
  `grep -rn <szimbólum> --include=*.go . | grep -v _test.go` VAGY `deadcode ./...` kimenet.
  A kimenetben production call site kell, a `_test.go` találat nem számít.
- **Nem nyúlsz** `.github/workflows/**`-hoz, a mutation/coverage scriptekhez, baseline fájlokhoz
  (a #169 külön munka). Ha egy issue ezt kívánná, jelezd, ne tedd meg.
- **Nem mergelsz**, nem zársz issue-t, nem pusholsz `main`-re. Csak feature ágra pusholsz és
  PR-t nyitsz. A merge a tulajdonosé.
- Helyi kapuk (`make` célok, `go test ./...`, `cargo test`, ami az adott PR-t érinti) zöldek a
  PR nyitása előtt; a kimenetet idézd. Ne használd a CI-t kapuként.
- Compose projektnév-ütközés: ha `docker compose`-t használsz, ellenőrizd, hogy a konténer
  a saját workspace-klónodat mountolja.
- **Határjelzés**: ha egy issue egy nyitott kérdésre épül, amit a kód nem dönt el, vagy a
  javítás nagyobb, mint az issue állítja, ne gyárts magabiztos rossz kimenetet: állj meg, írd le
  mi csúszik meg és mi kell hozzá, és lépj a következő független issue-ra.
- A sorrend a függőségeket követi, de egy megakadt issue nem blokkolja a független
  követőit.

## Output

`output/` alá, magyarul:
- `output/queue-status.md` — táblázat: issue · PR URL · ág · HEAD commit · helyi kapuk eredménye ·
  státusz (PR nyitva / megakadt / diagnózis) · a "javítás nélkül bukik" bizonyíték helye.
- Minden `output/issue-<n>.md` végén claim-evidence tábla, fejléce pontosan:
  `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`
- `output/issue-<n>.md` — issue-nként: mit találtál a kódban (állítás-ellenőrzés az issue
  szövegével szemben), mi változott, hívási út `file:line`, nyitott kérdések.
- A kód a CIC_Relay PR-okban él, nem az output-ban.

## Git instrukciók

- cic-factory: csak a `feature/relay-issue-queue-01` ágra commitolsz és pusholsz.
- CIC_Relay: a saját feature ágaidra pusholsz, PR-t nyitsz; a base a default ág.
- Commit üzenetben nincs `Co-Authored-By` vagy AI-jelölő sor.
- Friss klónban nincs Vault-aláírás és placeholder az identitás: ezt jelezd a PR-ban, ne
  titkold; a tulajdonos kezeli.

## Nyelvi szabály

Dokumentáció és output: magyar. Forráskód, teszt, commit, PR, issue-komment: angol.
