# wasm-template-release-contracts — Schema-igazítás + verify-release CLI

## Reasoning mód

**implementation** — a `wasm-template-contracts` (PR #12, mergelve a `wasm/main`-be,
HEAD `e06ed9c`) folytatása. Külső review 2. tier-je: a dokumentált szerződés
(`docs/contracts/*`, `abi:` blokk, `metadata.buildHash`) erősebb, mint a géppel
kikényszerített séma — ezt zárja be ez a job egy géppel ellenőrizhető
`verify-release` paranccsal és a `project.schema.yaml` valós tartalom-igazításával.

**Nem redesign.** A canonical release path (`tools/infra.py`, `tools/compiler.py`,
`tools/finalize_release.py`) és a `schemas/main` öröklött release-backbone
kérdése **külön (Tier 3 audit) jobban** van — ld. "Nem ebben a jobban".

## Munkakörnyezet — branch szabály (KÖTELEZŐ)

- base-repo klón a workspace-edbe, `git fetch origin wasm/main`.
- `origin/wasm/main` HEAD-je `e06ed9c` legyen (tartalmazza PR #11 + #12-t —
  `git log --oneline -3 origin/wasm/main`-nel ellenőrizd: `e06ed9c`, `019aac5`,
  `1527d05` kell legyen a top 3 commit). Ha nem ez a HEAD, állj meg és jelezd a
  riportban — ne találgass másik bázist.
- Branch: **`wasm/f/release-contracts`** a `wasm/main`-ből.
- Minden base-repo commit a `wasm/f/release-contracts`-ra. Push **kizárólag**
  ide. PR: `gh pr create --base wasm/main --head wasm/f/release-contracts`
  (ha a `gh`/remote környezeti korlát miatt nem megy, dokumentáld — az
  orchestrátor megnyitja).

## Feladat

### 1. `project.schema.yaml` igazítása a valós `project.yaml`-hoz

A jelenlegi `project.yaml` tartalmaz mezőket (`abi:`, `metadata.buildHash`,
`createdBy`, `cicSign`, `validatedBy`, stb.), amiket a `project.schema.yaml`
nem (vagy csak gyengén) modellez. Vedd sorra a `project.yaml` tényleges
top-level és `metadata`/`abi` kulcsait, és a schema-ban:
- adj típust és (ahol értelmes) kötelezővé tételt minden meglévő mezőnek,
- az `abi:` blokkot **külön `abi.schema.yaml`** fájlban definiáld
  (name/version/envelopeVersion/exports/operations — string/array/int
  típusokkal, `exports`/`operations` nem-üres string-array), és a
  `project.schema.yaml`-ból `$ref`-fel hivatkozz rá,
- mérlegeld `additionalProperties` szigorítását, de **csak ott ahol a
  template/TBD mezők ezt nem törik** — ha töri, dokumentáld és hagyd lazán,
  ne hazudj szigorúságot.

`make validate` (`python -m tools.compiler validate`) ezután is `exit 0`
legyen a jelenlegi `project.yaml`-on.

### 2. `verify-release` parancs

Új, önálló eszköz (`tools/verify_release.py` + `make verify-release` target),
amely **offline**, egyetlen futtatással ellenőrzi:
1. `project.yaml` schema-validáció (az 1. pont schema-ja ellen),
2. `module/module.wasm` SHA-256 == `project.yaml metadata.buildHash`
   (a `wasm.rebuild-verify` logikájának újrafelhasználásával vagy hívásával —
   NE duplikáld a tinygo build logikát, hívd meg azt),
3. `abi.exports` == `module/module.wasm` tényleges exportjai (a
   `module/abi_manifest_test.go` logikájának CLI-szintű megfelelője, vagy a
   teszt futtatása `go test -run ...`-tal),
4. `MANIFEST.sha256` ellenőrzés (`make manifest-verify` hívása),
5. provenance-mezők (`createdBy`, `cicSign`, `validatedBy` vagy ezek
   ekvivalensei) jelenlétének/kitöltöttségének riportolása — **ne hamisíts
   kriptográfiai aláírás-ellenőrzést**, ha nincs hozzá Vault-hozzáférés;
   ha a mező hiányzik/TBD, jelezd `MISSING`/`TBD`-ként, ne `OK`-ként.

Kimenet: ember-olvasható összefoglaló (`PASS`/`FAIL` minden 1-5 ponthoz),
non-zero exit ha bármelyik ellenőrizhető pont `FAIL`. A `tools/finalize_release.py`-t
**ne módosítsd** — ha a `verify_release.py`-nak szüksége van a benne lévő
logikára, importáld/hívd meg függvényként, vagy másold ki a releváns
ellenőrző logikát (ne a fájlt módosítsd).

CI-be kötés **opcionális** ebben a jobban — ha beköted (`.github/workflows/ci.yml`),
külön step legyen, és dokumentáld miért éppen ott (pl. a `manifest-verify` után).
Ha nem kötöd be, dokumentáld a riportban miért (pl. release-szakaszhoz kötött,
nem minden push-hoz releváns).

### 3. Dokumentáció

- README.md / README.hu.md — `verify-release` Makefile Commands bullet.
- `docs/contracts/{en,hu}/release-artifact.md` — frissítsd a "Target state"/
  "Célállapot" szakaszt: a `verify-release` parancs immár **implemented**
  (a `wasm-template-contracts` jobban ez még célállapot volt) — pontosítsd mi
  van már meg és mi még nem (pl. kriptográfiai aláírás-ellenőrzés még TBD).

## Nem ebben a jobban

- **`tools/infra.py`, `tools/compiler.py`, `tools/finalize_release.py`
  módosítása TILOS** ebben a jobban (a `verify_release.py` ezeket csak hívja/
  importálja, nem módosítja).
- Doc status modell kiterjesztése minden szekcióra, CI gate-ek általános
  szétszedése egy `quality` step alól — későbbi job.
- A `tools/finalize_release.py` `checksum == buildHash` jellegű örökölt
  logikájának érdemi felülvizsgálata, és a canonical release path tisztázása
  — ezt egy párhuzamos **`wasm-release-pipeline-audit`** job végzi (csak
  feltérképezés, nincs implementáció). Ha munkád közben ebbe a területbe
  futnál, dokumentáld "blocked by release-pipeline audit" megjegyzéssel, és
  ne nyúlj hozzá.

## Tiltott rövidítések (kötelező)

- **Schema-bővítés ≠ valódi validáció.** Minden új/szigorított schema-mezőre
  mutass egy konkrét esetet (futtatás-kimenet), ahol egy hibás `project.yaml`
  a régi schema-val átment volna, az újjal pedig elbukik (vagy fordítva: ha
  nincs ilyen eset, dokumentáld miért nem volt rá szükség).
- **`verify-release` zöld ≠ release-ready.** A riportban explicit listázd mi
  az, amit a parancs NEM ellenőriz (pl. kriptográfiai aláírás), hogy a
  "PASS" ne keltsen hamis biztonságérzetet.
- A fájl léte ≠ implemented — `make verify-release`, `make validate`,
  `make manifest-verify` tényleges futtatás-kimenetét idézd.
- `tools/infra.py`/`tools/compiler.py`/`tools/finalize_release.py` módosítása
  — TILOS.

## Reachability — kötelező bizonyíték

- `grep -rn` a kulcs-bekötésekre: `abi.schema.yaml` `$ref` a
  `project.schema.yaml`-ból, `verify-release` make target, `tools/verify_release.py`
  hívásai a `wasm.rebuild-verify`/`manifest-verify` logikára.
- Teljes verifikációs lánc: `make validate`, `make manifest-verify`,
  `make wasm.build`, `make wasm.rebuild-verify`, `make wasm.test`,
  `make verify-release`, `make golang.quality`, `make check`, `make test`,
  `make docs.link-check`.

## Output

- `jobs/wasm-template-release-contracts/output/wasm-template-release-contracts-report.md` —
  claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`),
  az 1-3 pont egyenként lefedve + "amit `verify-release` NEM ellenőriz" lista.
- base-repo `wasm/f/release-contracts` pusholva + PR a `wasm/main` bázisra
  (vagy dokumentált korlát, ha a PR megnyitás nem megy).

## Git instrukciók

- base-repo: commit + push **csak** `wasm/f/release-contracts`-ra; PR bázis: `wasm/main`.
- cic-factory: commit + push **csak** `feature/wasm-template-release-contracts`-ra.
- Main-re és `wasm/main`-re sehova nem pusholsz.

## Definition of Done

- [ ] `wasm/f/release-contracts` branch a `wasm/main`-ből (`e06ed9c`), minden munka ott
- [ ] `abi.schema.yaml` létezik, `project.schema.yaml` rá `$ref`-el
- [ ] `project.schema.yaml` a valós `project.yaml` mezőit modellezi (típus + kötelezettség)
- [ ] `make validate` zöld a jelenlegi `project.yaml`-on
- [ ] `tools/verify_release.py` + `make verify-release` — 1-5 pont ellenőrizve, futtatás-kimenettel
- [ ] README + `docs/contracts/release-artifact.md` frissítve
- [ ] teljes verifikációs lánc zöld a builder konténerben, kimenetek idézve
- [ ] PR megnyitva (`wasm/f/release-contracts` → `wasm/main`) vagy dokumentált korlát
- [ ] report + claim-evidence tábla a `feature/wasm-template-release-contracts`-on pusholva
- [ ] `tools/infra.py`/`tools/compiler.py`/`tools/finalize_release.py` nem módosult

## Nyelvi szabály

- Dokumentáció, jelentés: **magyarul** (kivéve base-repo README/docs, en+hu pár)
- Go/Python/Makefile/shell/YAML, kódon belüli komment, commit message: **angolul**
