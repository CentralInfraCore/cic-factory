# review — relay-ci-build-audit

- Reviewer: orchestrátor (Claude Opus 5)
- Dátum: 2026-07-25
- Feature branch: `feature/relay-ci-build-audit`
- Review-zott commit: `1c95051` (job: relay-ci-build-audit — output)
- Job költsége: **$1.6311** · 51/60 turn · 597936 ms

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | **GO** | K1–K11, futtatva a régi (main) és az új (PR #26) validátorral is |
| `tools/validate-output.sh` | **GO** | 3 fájl, 18 feloldott `file:line`; WARN: 69 feloldatlan hivatkozás |
| CI | n/a | a cic-factory repóban nincs CI workflow erre az útra |

Az O5 WARN nem tartalmi hiba: a feloldatlan hivatkozások túlnyomó része
`fájl.go:87-89` alakú **tartomány** vagy könyvtár nélküli puszta fájlnév, amit a
validátor egyszerű `path:line` heurisztikája nem tud feloldani.

## Amit ténylegesen ellenőriztem

Az agent két legterhelőbb állítását **függetlenül újraverifikáltam** a relay
forrásán, nem a summaryból fogadtam el.

| Állítás az outputban | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| #5: a `build_hash`/`verification_root` a relay **saját** build-adataira mutat, nem a vizsgált repóra | `sed -n '710,718p' cmd/relay/main.go` + `sed -n '245,252p' core/modules/schemacompile/schemacompile.go` | **IGAZOLVA.** `bctx := merkle.BuildContext{SourceRef: CommitHash, SourceTreeDigest: SourceTreeHash, …}` — szerver-indításkori konstansok; a `merkle.VerificationManifest.Source` ezeket veszi át |
| #3: `ci.build@1.0` nincs egyik workflow `Steps[]`-jében sem | `sed -n '117,134p'` és `sed -n '213,234p' cmd/relay/bootstrap.go` — **mindkét Steps lista teljes egészében kiolvasva** | **IGAZOLVA.** `cic.schema.compile`: assert → build → sign. `cic.schemas.pipeline`: start → test → validate → release → assert → build → sign. `ci.build@1.0` egyikben sem szerepel |
| `ci.build` regisztrálva van bootstrapban | `grep -n 'ci\.build\|ciBuildFuncs' cmd/relay/bootstrap.go` | **IGAZOLVA.** `bootstrap.go:55` + `:64` (`PutModule`). Leírása: *„runs a make target and returns the artifact SHA-256 digest"* |
| A `ci.build` státusza **scaffold** | a fenti kettő együtt: betöltődik, de kérésből elérhetetlen | **IGAZOLVA** — pontosan a saját scaffold-definíciónk esete |
| Az output-fájlok tényleg a specben megnevezettek | `tools/validate-output.sh` O1 | **IGAZOLVA** (gépi) |
| A claim-evidence tábla formátuma megfelel | `validate-output.sh` O2 | **IGAZOLVA** (gépi) |

## Amit NEM ellenőriztem

A csend nem azt jelenti, hogy rendben van.

- **A többi 7 rés** (#1, #2, #4, #6, #7, #8, #9) — nem verifikáltam egyenként.
  Mindegyik mellett van `file:line`, és a két mintavett állítás pontosnak
  bizonyult, de ez nem bizonyítja a maradékot.
- **A #4-es rés dinamikus viselkedése** — az agent maga is jelzi a Kockázat
  oszlopban, hogy nem futtatta élesben a pipeline-t; a mezőkiesés statikus Go
  map-literál szemantikából levezetve. Én sem futtattam.
- **A `deadcode` reachability** — nincs telepítve a relay környezetben
  (`deadcode: command not found`), így a #3 grep-alapú. A Steps-listák
  teljes idézése ezt kompenzálja, de nem egész-program call-graph.
- **A Makefile ldflag lánc** (`-X main.SourceTreeHash=…`) — az agent sem
  olvasta el, én sem.
- **Van-e más CI-orchestrátor image** a relay repóban a gyökér `Dockerfile`-on
  kívül — az audit hatóköre a spec szerint csak a két gyökérfájl volt.

## Nyitott tétel — a `kb_focus` nem oldódott fel

Az agent mind a négy `kb_focus` chunkra (`c781`, `c912`, `c927`, `c365`)
`{"result": null}`-t kapott, `manifest.graph_stale: true` mellett.

Ez **ellentmond a session eleji saját boot sequence-emnek**, ahol ugyanezt a
négy chunkot sikeresen elolvastam, tartalommal. Nem tudom most feloldani: a
`cic-graph` MCP az orchestrátor oldalán menet közben leállt
(`Unable to connect`), tehát nem tudom újrapróbálni. Az agent oldalán a szerver
**válaszolt** (null-t adott), nálam **nem is kapcsolódik** — ez két különböző hiba.

Lehetséges okok, egyik sem igazolva: KB újragenerálás menet közben chunk-id
eltolódással · az agent más adathalmazt látott · a `graph_stale` flag valós
indexelési probléma. **Következő session elején tisztázandó**, teljes restart után.

**Ami ettől függetlenül igazolt:** a P2 mechanizmus működik — a `kb_focus`
mechanikusan bekerült a promptba (`[*] kb_focus injektálva: c781 c912 c927 c365`).
A rés az adatforrásban van, nem az injektálásban.

## Mérési hiba a saját instrumentációmban

A `usage.input_tokens: 1525` **félrevezető** egy olyan futásnál, ami 16 KB+
forráskódot olvasott. A `claude --output-format json` `usage` mezője az utolsó
üzenet használatát adja vissza, nem a kumulatívat, és a `cache_read_input_tokens` /
`cache_creation_input_tokens` mezőket a `run-job.sh` jelenleg **eldobja**.

Az aggregált, megbízható szám a `cost_usd` ($1.6311). A token-mezők jelenlegi
formában nem azt jelentik, amit egy olvasó feltételezne. **Javítandó**
(cache-mezők felvétele vagy a mezők átnevezése) — külön, kis job.

## Döntés

**MERGE.** A job azt szállította, amit a spec kért: kilenc rés, mind
`file:line` bizonyítékkal, megoldási javaslat nélkül (ahogy előírtuk), és a
relay repót nem érintette. A két mintavett állítás független újraverifikáción
átment. Az agent a Kockázat oszlopban maga jelezte a saját korlátait — ez a
kívánt viselkedés.

A nem ellenőrzött 7 rés a következő lépés (interfész-spec) bemenete lesz; ott
azok egyenkénti verifikációja kötelező, mielőtt a relay-csapat felé bármit állítunk.
