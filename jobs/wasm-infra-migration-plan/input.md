# wasm-infra-migration-plan — `tools/infra.py` / `tools/compiler.py` / `project.schema.yaml` migrációs terv

## Reasoning mód

**audit** — felderítő/tervező, **nem implementáció**. A cél a
`wasm-schemalib-sync-plan` riport 3. és 5. lépésének (`tools/infra.py` swap,
`tools/compiler.py` validate-routing) **végrehajtható migrációs terve**,
function/blokk-szintű ADOPT / PRESERVE / SKIP döntéssel és pontos
file:line célokkal — egy következő implementációs sub-job ezt fogja
végrehajtani.

Források:
- `cic-factory/jobs/wasm-schemalib-sync-plan/output/wasm-schemalib-sync-plan-report.md`
  — "Claim-evidence tábla — `tools/infra.py`" és "— `tools/compiler.py`"
  szakaszok (function-szintű diff-leltár, már elvégzett munka — ezt NE
  ismételd meg, hanem ÉPÍTS rá).
- `cic-factory/jobs/wasm-validation-gate-audit/output/wasm-validation-gate-audit-report.md`
  — Feladat A/B futtatott bizonyítékai.
- KB node `c1295`.

## Munkakörnyezet

- `CIC-Schemas` klón: checkout `2ec57c0` (sync-plan riport referenciája).
- `base-repo` klón: `wasm/main` HEAD (jelenleg `b7da285`, post-PR#17 —
  ellenőrizd `git log --oneline -1`-lel, és ha eltér a tervben jelzettől,
  jelezd a riportban).

---

## Előre eldöntött korlátok (NE vizsgáld felül, ezek orchestrátor-döntések)

1. **`_validate_final_project_yaml` MARAD a base-repo saját verziója**
   (`tools/infra.py:168-211`, hardcoded `project.schema.yaml` +
   `metadata.buildHash` kötelezőség-check). A `wasm-validation-gate-audit`
   futtatott bizonyítékkal igazolta, hogy a CIC-Schemas `schemalib`-es
   verziója (`tools/infra.py:84-109`) `KeyError: 'spec'`-tel elhasal saját
   `project.yaml`-jára — egy 1:1 csere **regresszió** lenne. → ezt a
   függvényt a migrációs tervben **PRESERVE**-ként kell rögzíteni, módosítás
   nélkül.

2. **`tools/compiler.py` `validate` subcommand → `_validate_final_project_yaml()`**
   (nem `manager.run_validation()`). Indoklás: a base-repo jelenlegi
   `run_validation()` (`tools/infra.py:488-509`) egy no-op placeholder
   (`# Placeholder for full validation logic`), tehát a váltás nem vesz el
   funkciót — viszont a CIC-Schemas-os `run_validation` `_require_repo_type
   ("validate","schema")`-t hívna, ami `wasm/main`-en (`repo_type` nincs
   beállítva → default `"module"`) `ReleaseError`-ral elhasalna
   (`wasm-validation-gate-audit` Feladat B, futtatott bizonyíték). A
   `_validate_final_project_yaml` már most működő, valódi validációt végez.

A migrációs tervnek ezt a két pontot **adott korlátként** kell kezelnie —
a terv feladata a TÖBBI diff-tétel (sync-plan riport `tools/infra.py` és
`tools/compiler.py` táblái, ~9-10 sor) ADOPT/PRESERVE/SKIP besorolása ezen
korlátok mellett.

---

## Feladat — Migrációs tábla összeállítása

A sync-plan riport `tools/infra.py` és `tools/compiler.py` claim-evidence
táblái alapján, **minden** ott felsorolt diff-tételre (kivéve a fentebb már
eldöntött `_validate_final_project_yaml` és `run_validation`/`validate`
routing tételeket) határozd meg:

- **ADOPT** — vedd át a `CIC-Schemas` verzióját (mert javítás/refaktor és
  wasm-nek nem ártalmas)
- **PRESERVE** — tartsd meg a base-repo saját verzióját (wasm-specifikus,
  elvesztése funkcióvesztés)
- **SKIP** — ne vedd át, ne is őrizd külön — a `CIC-Schemas`-os tétel a wasm
  modulnak irrelevánsnak minősül (pl. soha nem hívott kódág)

Minden döntéshez add meg: pontos `tools/infra.py` / `tools/compiler.py` /
`project.schema.yaml` file:line tartomány **mindkét repóban** (forrás és cél),
és egy mondatos indoklást.

**Konkrétan dolgozd fel ezeket a sync-plan-riportban azonosított tételeket**
(a riport sor-hivatkozásai irányadók, de ellenőrizd a jelenlegi `b7da285`-ön —
ha a sorszámok eltolódtak a PR #17 schemalib-transzfer miatt, jelezd és
korrigáld):

1. `to_canonical_json`, `get_sha256_hex`, `parse_certificate_info`,
   `ValidationFailureError` — modul-szintű primitívek `schemalib`-ből.
   (Megjegyzés: a `wasm-schemalib-transfer` job ezeket **már átemelte**
   `base-repo/tools/schemalib/`-be — ellenőrizd `grep -rn "from .schemalib\|
   from tools.schemalib" base-repo/tools/infra.py`-vel, hogy `infra.py`
   már importálja-e ezeket, vagy még a régi modul-szintű def-eket
   tartalmazza duplikálva.)
2. `load_and_resolve_schema`/`load_yaml`/`write_yaml` — a `schemalib.loader`
   verzió JSON round-trip-et végez (`JsonRef` proxy → plain dict), a
   base-repo jelenlegi verziója nyers `JsonRef` objektumot ad vissza
   (`tools/infra.py:82`: `return resolved_data`). **Futtatott bizonyíték
   kötelező**: írj egy eldobható `/tmp/` szkriptet, amely mindkét
   `load_and_resolve_schema`-implementációval betölti `base-repo/project.schema.yaml`-t,
   és az eredményt átadja `jsonschema.validate(instance=<base-repo/project.yaml>,
   schema=<eredmény>)`-nek — idézd mindkét eset kimenetét (siker vagy
   traceback). Ez dönti el, hogy `base-repo/tools/verify_release.py:54`
   törne-e a csere után.
3. `_execute_developer_preparation_phase` checksum/signing —
   `schemalib.artifact` primitívek (`compute_spec_checksum`,
   `build_signing_payload`) vs base-repo kézi implementációja. A sync-plan
   riport "alacsony kockázat"-ot jelez, de a `createdBy` build-up sorrendje
   eltér. **Futtatott bizonyíték**: ha `base-repo/tests/test_tools/` van
   teszt ami ezt a metódust fedi, futtasd (`docker compose exec builder
   python -m pytest <path> -v`), idézd PASS/FAIL-t.
4. `_resign_with_build_hash` + hívása `_execute_finalization_phase`-ből
   (`tools/infra.py:352-385`, hívás `:406`) — **PRESERVE** (wasm-specifikus,
   a sync-plan riport "magas kockázat"-ot jelez törlésnél). Erősítsd meg a
   pontos jelenlegi file:line-t `b7da285`-ön.
5. `finalize_release.py` DEPRECATED komment (`tools/infra.py:352-385`-re
   hivatkozik) — ha a 4. pont PRESERVE, a komment érvényben marad-e, vagy
   pontosítást igényel? Idézd a komment szövegét és a hivatkozott
   file:line-t `b7da285`-ön.
6. `_get_repo_type`/`_require_repo_type`/`run_release_dependency`/
   `run_release_schema`/`_execute_schema_release` — additív, `schemas/main`-
   specifikus metódusok. Mivel a 2. korlát szerint `wasm/main` `validate`
   subcommand-ja NEM `run_validation`-t hívja, és `repo_type=module` esetén
   ezek a metódusok sosem futnának wasm-on — javasolj ADOPT vagy SKIP
   döntést, indoklással (komplexitás vs. jövőbeli konzisztencia
   `schemas/main`-nel).
7. `project.schema.yaml` `compiler_settings` blokk additív mezői
   (`repo_type` enum, `main_branch`, `dependencies_dir`, `release_dir`,
   `validity_days`, stb.) és `additionalProperties: false` (`:185`,
   `wasm/main`-en megvan, `schemas/main`-ben nincs). Határozd meg: ha
   `wasm/main` átveszi a `schemas/main` `compiler_settings` definícióját,
   kell-e `repo_type: module`-t felvenni a `wasm/main` `project.yaml`-jába
   (figyelem: a 2. korlát miatt ennek `validate`-re nincs hatása — csak
   dokumentációs/konzisztencia kérdés), és mi történjen az
   `additionalProperties: false`-szal (megtartás javasolt — ne veszítse el
   a wasm-oldali config-typo védelmet).
8. `project.schema.yaml` `metadata` blokk wasm-specifikus 9 extra mezője
   (`tags`, `validatedBy`, `createdBy`, `build_timestamp`, `validity`,
   `checksum`, `sign`, `buildHash`, `cicSign`, `cicSignedCA`,
   `base-repo/project.schema.yaml:47-133`) — **PRESERVE**, erősítsd meg a
   jelenlegi file:line-t `b7da285`-ön.

---

## Tiltott rövidítések (kötelező)

- **Statikus olvasás ≠ működik.** A 2. és 3. pont (load_and_resolve_schema
  viselkedés, signing-sorrend teszt) esetén **futtatott** bizonyíték
  (szkript-kimenet vagy pytest-output) kötelező — "elméletileg működnie
  kellene" nem elfogadható.
- **Ne módosíts** semmilyen production fájlt sem a `base-repo`, sem a
  `CIC-Schemas` klónban. Az eldobható kísérleti szkriptek `/tmp/` alá
  kerülnek, nem kerülnek commitba.
- **Ne implementálj** semmilyen migrációs lépést — a feladat a TERV, nem a
  végrehajtás. Ha egy ADOPT-döntéshez konkrét kódrészlet (snippet) segítené
  a következő job-ot, idézd a forrás file:line-t — ne írj új kódot a
  base-repo-ba.
- Az 1. és 2. (Előre eldöntött korlátok) pontokat **ne vizsgáld felül és ne
  indokold újra** — ezek lezárt döntések, vedd adottnak.

---

## Reachability / futtatási bizonyíték

Python réteg, `deadcode`/`_test.go` nem releváns (N/A). A 6. pont
(`_get_repo_type` stb. ADOPT/SKIP) esetén `grep -rn` eredménnyel igazold,
hogy `base-repo`-ban jelenleg sehol nem hívják ezeket (0 találat → SKIP felé
mutat).

---

## Output

`jobs/wasm-infra-migration-plan/output/wasm-infra-migration-plan-report.md`:

- Claim-evidence tábla minden 1-8. tételre: `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat` — "Állítás" = a tételhez tartozó
  ADOPT/PRESERVE/SKIP döntés + cél file:line; "Státusz" = confirmed/N/A.
- Migrációs tábla (a claim-evidence tábla mellett, kiegészítő): `Tétel |
  Döntés (ADOPT/PRESERVE/SKIP) | Forrás file:line (CIC-Schemas) | Cél
  file:line (base-repo) | Indoklás`
- A 2. és 3. pont futtatott bizonyítékainak teljes kimenete (szkript-output
  / pytest-output idézve).
- Záró szakasz: a következő (implementációs) sub-job számára egy sorrendezett
  lépéslista (mit kell módosítani melyik fájlban, milyen sorrendben, hogy a
  `make check`/`make test` mindvégig zöld maradjon).

## Git instrukciók

- `cic-factory`: commit + push **csak** `feature/wasm-infra-migration-plan`-ra.
- `base-repo` és `CIC-Schemas`: **semmilyen módosítás, semmilyen commit/push**
  — tisztán olvasás + `/tmp/` alatti eldobható szkriptek.

## Nyelvi szabály

- Riport: **magyarul**
- Kódidézetek, parancsok, commit message: **angolul**
