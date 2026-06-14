# wasm-infra-migration-impl — `tools/infra.py` migráció végrehajtása (Opció 1, 3-4. lépés)

## Reasoning mód

**implementation**. A `wasm-infra-migration-plan` job (lásd
`cic-factory/jobs/wasm-infra-migration-plan/output/wasm-infra-migration-plan-report.md`,
"Sorrendezett lépéslista a következő (implementációs) sub-jobnak" szakasz,
1-12. pont) elkészítette a pontos, file:line-szintű migrációs tervet —
ez a job **végrehajtja** azt.

Források:
- `cic-factory/jobs/wasm-infra-migration-plan/output/wasm-infra-migration-plan-report.md`
  — teljes riport: claim-evidence tábla (1-8. tétel), migrációs tábla, a két
  futtatott bizonyíték (`load_and_resolve_schema`, `createdBy` build-up), és
  a 12 lépéses lépéslista. **A lépéslistát kövesd sorrendben, lépésszámokkal
  hivatkozva a riportodban.**
- `cic-factory/jobs/wasm-validation-gate-audit/output/wasm-validation-gate-audit-report.md`
  — a `_validate_final_project_yaml` PRESERVE és a `validate`-routing döntés
  háttere (11. lépéshez).
- `CIC-Schemas/tools/infra.py:143-192` (`2ec57c0`) — referencia-implementáció
  az 5. lépéshez (`compute_spec_checksum`, `build_signing_payload`, kétlépéses
  `createdBy`).
- KB node `c1295`.

## Munkakörnyezet

- `base-repo` klón: hozz létre egy **`wasm/f/infra-migration`** branch-et
  `wasm/main`-ből (jelenleg `b7da285` — ellenőrizd `git log --oneline -1`-lel,
  ha eltér, jelezd a riportban és dolgozz a tényleges HEAD-en).
- `CIC-Schemas` klón: csak referenciaként (`2ec57c0`), **nem módosítod**.

---

## Feladat — a 12 lépés végrehajtása

Hajtsd végre `cic-factory/jobs/wasm-infra-migration-plan/output/wasm-infra-migration-plan-report.md`
"Sorrendezett lépéslista" szakaszának 1-12. pontját, **ebben a sorrendben**,
a `base-repo` `wasm/f/infra-migration` branch-én. Minden lépés után futtasd:

```
python3 -m pytest tests/test_tools/ -q --no-cov
```

(vagy `docker compose exec builder python -m pytest tests/test_tools/ -q` ha
a Docker builder elérhető) — a **31 jelenlegi teszt + a
`TestValidateFinalProjectYamlRealSchema` osztály tesztjei mindvégig PASS**
kell maradjanak. Ha egy lépés után FAIL jelenik meg, **álld meg, diagnosztizáld,
és a riportban dokumentáld a javítást** (ne menj tovább törött állapotból).

### Kiemelt pontok a 12 lépésből

- **1-3. lépés** (import-bővítés + duplikált primitívek törlése): a riport
  240. sora szerint **ellenőrizd**, hogy a PRESERVE-elt
  `_validate_final_project_yaml`/`_resign_with_build_hash` (4-5. lépés
  hatóköre) nem hivatkozik-e közvetlenül `JsonRef`/`hashlib`/`base64`-ra,
  amit a törlendő modul-szintű def-ek hoztak be — ha igen, tartsd meg vagy
  add hozzá ezeket az importokat.
- **4. lépés** (re-grep): a riport a sor-eltolódást **becsült** értékkel
  (`~261-294`/`~315`) adta meg — a **te** re-grep-ed adja a tényleges
  értéket; ezt a `finalize_release.py` komment frissítéséhez (7. lépés)
  és a riportodban is használd.
- **5-6. lépés** (`_execute_developer_preparation_phase`,
  `_resign_with_build_hash` átírása): a `wasm-infra-migration-plan` riport
  3. és 4. tétele **futtatással igazolta**, hogy a két variáns bit-azonos
  `metadata` dict-et ad — a te feladatod ezt **a valódi kódba átvinni**,
  majd a teszteket futtatva **megerősíteni**, hogy ez élesben is igaz.
- **9-10. lépés** (`project.schema.yaml` + `project.yaml` sync, 7a/7b/8a/8b
  tételek): a riport 177-224. sora tartalmazza a tömörített diff-térképet —
  kövesd pontosan, **PRESERVE** tételeket (7b, 8a, 8b) szó szerint hagyd meg,
  **ADOPT** tételeket (7a, 7c) vedd át a `CIC-Schemas/project.schema.yaml`/
  `project.yaml`-ból.
- **11. lépés** (`tools/compiler.py` validate-routing): a riport ezt
  "NINCS módosítás szükséges"-ként zárja, de ezt **ne fogadd el készként** —
  **ellenőrizd futtatással**: a `wasm-infra-migration-plan` "Előre eldöntött
  korlát #2" (forrás: `wasm-validation-gate-audit` Feladat B) azt mondta, hogy
  a `validate` subcommand `_validate_final_project_yaml()`-t hívjon
  `manager.run_validation()` helyett, mert az utóbbi no-op placeholder. A
  6. tétel SKIP-je (nincs `_require_repo_type` gate átvétel) miatt a riport
  azt állítja, hogy ez most már nem szükséges. **Te erősítsd meg vagy vond
  vissza ezt az állítást**: futtasd `python -m tools.compiler validate
  --project project.yaml` (vagy a megfelelő CLI hívást) a migráció UTÁN, és
  idézd a kimenetet. Ha `run_validation()` még mindig no-op-ot logol
  (`✓ Validation successful` érdemi ellenőrzés nélkül), és emiatt `make
  validate`/`make check` érdemi validációt **nem** végez, **implementáld a
  constraint #2 routing-cseréjét** (`validate` subcommand →
  `_validate_final_project_yaml()`), és dokumentáld a döntést +
  futtatott bizonyítékot a riportban. Ha a futtatott bizonyíték azt mutatja,
  hogy a két validációs út valójában más célt szolgál (pl.
  `canonical_source_file` vs `project.yaml`) és mindkettő szükséges, ezt is
  dokumentáld — és NE törölj funkciót.
- **Manifest**: a módosított fájlok miatt futtasd `make manifest-update`-et
  (lásd `Makefile:97-98`), majd `make manifest-verify`-jal igazold, hogy
  tiszta. Idézd mindkét parancs kimenetét.
- **`make check`** (black/isort/ruff/mypy/bandit, `docker compose exec
  builder` vagy lokális venv): futtasd a végén, és ha bármi FAIL-t ad a
  módosított fájlokra, javítsd (ld. `wasm-schemalib-transfer` job tapasztalata:
  formázás/lint/typecheck/security mindig EXIT=0 kell legyen mielőtt PR-t
  nyitunk).

---

## Tiltott rövidítések (kötelező)

- **"31/31 PASS" ≠ sikeres migráció.** Minden ADOPT-lépésnél (1-3, 5-6, 9-10)
  add meg a **diff**-et (előtte/utána, releváns hunk) — a teszt-zöld önmagában
  nem bizonyítja, hogy a logika valóban a tervezett forrásból jött át.
- **Ne térj el** a 12 lépés sorrendjétől és tartalmától magyarázat nélkül. Ha
  egy lépés végrehajtása közben a tényleges kód eltér a tervtől (pl. más
  sorszámok, hiányzó import), **dokumentáld az eltérést és az általad hozott
  döntést** — ne hallgass el semmit.
- **Ne nyúlj** a 6. tételben (SKIP) felsorolt `_get_repo_type`/
  `_require_repo_type`/`run_release_dependency`/`run_release_schema`/
  `_execute_schema_release` metódusokhoz — ezek **nem** kerülnek át.
- **Ne módosíts** semmit a `CIC-Schemas` klónban — az csak referencia.
- A 11. lépésnél **ne fogadd el "nincs teendő"-t bizonyíték nélkül** — lásd
  fent.

---

## Reachability / futtatási bizonyíték

Python réteg, `deadcode ./...`/`_test.go`-alapú reachability nem releváns
(N/A). Helyette: a 4. lépés re-grep-jét **`grep -rn`**-nel végezd (pl.
`grep -rn "_resign_with_build_hash\|_execute_finalization_phase" tools/infra.py`),
és idézd a kimenetet a riportban. Minden ADOPT-lépés bizonyítéka: diff +
pytest-output. A 11. lépés bizonyítéka: a `validate` CLI-hívás (vagy `make
validate`) tényleges kimenete a migráció utáni állapoton.

---

## Output

`jobs/wasm-infra-migration-impl/output/wasm-infra-migration-impl-report.md`:

- Claim-evidence tábla a 12 lépésre: `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat` — "Állítás" = mit csináltál (file:line,
  ADOPT/PRESERVE forrás/cél), "Bizonyíték" = diff vagy parancs-kimenet.
- A pytest-futások kimenete minden lépés után (vagy legalább step-csoportonként,
  ha egy csoport egyben futtatható).
- `make manifest-update`/`make manifest-verify`/`make check` végső kimenete.
- A 11. lépés döntése + futtatott bizonyíték.
- Összefoglaló: melyik fájlok módosultak (file lista), és mi a státusza
  issue `CentralInfraCore/base-repo#16` 3-6. lépésének ezután (van-e
  hátramaradó nyitott pont a 6. lépésre — "teszt igazítások" — vagy minden
  lefedve).

## Git instrukciók

- `base-repo`: commit + push **csak** `wasm/f/infra-migration`-ra; PR bázis:
  `wasm/main`. Több commit is lehet (lépés-csoportonként), de a végállapotnak
  zöldnek kell lennie (`make check` + pytest).
- `cic-factory`: commit + push **csak** `feature/wasm-infra-migration-impl`-ra
  (a riport).
- `wasm/main`-re és `main`-re sehova nem pusholsz.

## Nyelvi szabály

- Riport: **magyarul**
- Kódidézetek, parancsok, commit message: **angolul**
