# cic-factory-core v0.2.0

Egy audit végigvitele. A `v0.1.2` óta tizenkét mért lelet, egy teljes M0
milestone, és a nyolc use-case szerződés normatívvá tétele.

Tag: `core/@v0.2.0` — 28 commit a `core/@v0.1.2` óta.

---

## Miért minor bump

Mert a `tools/env.sh` érintett. Aki átveszi, annak **hozzá kell nyúlnia a
konfigjához**, különben a job-specjeiben álló `${CIC_RELAY_PATH}` szó szerint
marad az agent promptjában. Ezt a
[Migráció](#migráció--amit-átvételkor-tenni-kell) szakasz írja le.

---

## Amit ez a verzió kikényszerít

| | |
|---|---|
| **a beágyazott Python is kód** | a `check-embedded-python.sh` lefordít minden `PY*` heredocot, és elutasítja a python3-nak adott heredocot, ami nem `PY*`-gal nyílik — az első futásán kettőt talált |
| **egy meta-olvasó, egy meta-író** | minden mezőolvasás a `meta-get.sh`-n, minden írás a `meta-set.sh`-n megy. Nincs több kézzel írt YAML-parser a repóban |
| **hiányzik ≠ olvashatatlan** | a `meta-get.sh` három exit code-ot ad; a megengedő ág csak a hiányra vonatkozik. Ami korábban tévedésből esett oda, az most fail closed |
| **a signer nem degradál** | CA nélkül a commit megáll. Nincs `curl -k`, a token nem az argv-ben utazik, és van timeout |
| **nevesített behelyettesítés** | az `input.md`-be csak felsorolt változók kerülnek be. A többi szó szerint marad — nem üresre cserélve |
| **azonosító-nyelvtan** | a `job-id` és az `agent-id` alakja ellenőrzött, mielőtt bármilyen path felépülne. A `--skip-spec-gate` ezt nem kerüli meg |
| **az index a metákat mondja** | valódi parse, szekció-hű mezőolvasás, és megjelöli az elakadt jobokat |
| **a szerződés nem ígérhet többet** | a `check-sequences.sh` elutasítja azt a use case-t, ami nem hordozza mind az öt részét, vagy `done`-utat ír le output-kapu és review nélkül |
| **a doksi nem állíthat nem létezőt** | a `check-docs.sh` D3/D4 és a `check-suite-counts.sh` a README-táblázatot, a K/O/C hivatkozásokat és a deklarált check-számokat a valósághoz köti |
| **a licenc egy helyen dől el** | a §7(b) kikötés a `LICENSE`-ben van, az AGPL-szöveg bájtra ellenőrizve |

Minden kapu bukását szándékosan elrontott másolaton mérték, mielőtt bekerült.
**21 suite, 475 check, 7 önálló checker.**

---

## Számok

| | `core/@v0.1.0` | `core/@v0.1.2` | `core/@v0.2.0` |
|---|---|---|---|
| assertion | 104 | 163 | **475** |
| viselkedési suite | 7 | 10 | **21** |
| önálló checker | 2 | 2 | **7** |
| gate-lépés | 14 | 14 | **38** |

---

## Amit NEM garantál

Ez az őszinte fele, és fontosabb a fentinél.

- **Párhuzamos futás nincs biztosítva.** Két job ugyanazt a live checkoutot,
  Git indexet és `jobs/index.yaml`-t írja. Nincs futás-identitás, lock vagy
  compare-and-swap. A szerződés annyi: **egy orchestrátor, egy checkout,
  egyszerre egy job.**
  ([#41](https://github.com/CentralInfraCore/cic-factory-core/issues/41))
- **És ez nincs is megmérve.** A `SPEC.md` UC-05 és UC-06 szakasza kimondja: az
  állítások az auditból származnak, nem lettek újramérve ebben a repóban. A
  kampány tizenkét másik leletét újramérte és mind reprodukálódott — ez teszi
  hitelessé az auditot, nem pedig okot ad a lépés kihagyására.
- **A review nincs eredményhez kötve.** Egy új attempt lezárható a korábbi
  attempt review-jával, mert a `close-job.sh` a fájlok meglétét nézi, nem azt,
  melyik futáshoz tartoznak.
  ([#43](https://github.com/CentralInfraCore/cic-factory-core/issues/43))
- **Az aláírás nem köti a commit identitását.** A payload a `git archive`
  szerinti fa — nem a commit OID, a szülők, a branch, a tag vagy a
  lifecycle-jelentés. A submodule commitok teljesen kimaradnak, és ez mérve is
  van: két különböző fa azonos aláírást adott.
  ([#38](https://github.com/CentralInfraCore/cic-factory-core/issues/38),
  [#44](https://github.com/CentralInfraCore/cic-factory-core/issues/44))
- **Az agent-hookok továbbra is tanácsadók.** A #27 és a #28 a hook saját
  sebezhetőségeit zárta le; a valódi határ a remote-oldali elfogadás, és az
  nincs meg.
  ([#10](https://github.com/CentralInfraCore/cic-factory-core/issues/10))
- **A mag még CIC-kötött.** `cic-graph`, `kb_focus`, `~/.claude-personal`. A
  runner-szerződés az executort leválasztotta, a session-kezelést nem.
  ([#42](https://github.com/CentralInfraCore/cic-factory-core/issues/42))

Aki erre épít, a fenti hat ponttal együtt épít rá.

---

## Migráció — amit átvételkor tenni kell

### 1. `FACTORY_PROMPT_VARS` a `tools/env.sh`-ba — kötelező

A `run-job.sh` már csak nevesített változókat helyettesít be az `input.md`-be.
Ez szándékos: korábban a teljes környezetet cserélte, ami egyszerre szivárgás
(egy exportált `$VAULT_TOKEN` a promptba került) és rongálás volt (a be nem
állított `$ref` és `$schema` üres stringre cserélődött a specekben).

```sh
export FACTORY_PROMPT_VARS="CIC_PARTNERS_ROOT CIC_RELAY_PATH CIC_SCHEMAS_PATH CIC_KB_PATH"
```

A mag ismeri a sajátjait (`JOB_ID`, `AGENT_ID`, `WORKDIR`, `FACTORY_CLONE`,
`FEATURE_BRANCH`, `CIC_JOB_ID`, `CIC_WORKDIR`). A telepítés a sajátjait itt adja
hozzá. Ha kimarad, a runner **szól** — de a beállítás az átvétel része, nem a
figyelmeztetésé.

### 2. PyYAML az orchestrátor gépén — új futásidejű függőség

A `close-job.sh`, a `check-stale-jobs.sh` és az `update-index.sh` mostantól
valódi YAML-parserrel olvas. Eddig csak a `validate-meta.sh` kérte a PyYAML-t.

```sh
bash tools/check-dependencies.sh        # ellenőrzi
bash tools/check-dependencies.sh --list # felsorolja, mit vár a gép
```

A teljes lista 15 parancs, 4 GNU-kapcsoló és 2 Python-modul. A GNU-kapcsolók
külön szerepelnek, mert a BSD/macOS `date`, `tar`, `find` és `stat` létezik,
csak mást csinál: **a repository Linux/GNU-t vár.**

### 3. A signer CA nélkül megáll

Nincs több `curl -k`. Ha a `$XDG_RUNTIME_DIR/vault/server.crt` (vagy a
`CIC_VAULT_CA_FILE`) hiányzik, a commit hibával áll le, ahelyett hogy a tokent
ellenőrizetlen csatornán küldené el.

### 4. Az `index.yaml` formátuma bővült

Új mezők: `stale:` a job soraiban, `totals.stale_jobs`, és
`status: "unreadable"` sor annál a jobnál, aminek a metája nem értelmezhető. Ez
utóbbi szándékos: kihagyva a job pont akkor válna láthatatlanná, amikor baj van
vele. Aki az indexet gépileg olvassa, számoljon ezekkel.

---

## Átvétel a cic-factory-ba — lemérve

A propagáció merge egy release tagről.

| | |
|---|---|
| konfliktus | **egy**: `LICENSE.md` |
| új fájl | 18 |
| módosuló fájl | 23 |
| a 44 meglévő job-id az azonosító-nyelvtanon | **mind átmegy** |
| az 51 meglévő `meta.yaml` a strict parseren | **mind átmegy**, duplikált kulcs nincs |

A `LICENSE.md` konfliktusa nem véletlen és nem is automatikusan feloldható: a
`cic-factory` licence **vegyes** (saját tartalom CC BY-NC-SA, átvett tooling
AGPL), a magé pedig most már AGPL + §7(b) attribution. A két dokumentum
szerkezete különbözik, és a `dependency.yaml` ownership-térképe egyikbe sem
sorolja a `LICENSE.md`-t. Az átvevőnek **el kell döntenie**, hogyan jelenik meg
a §7(b) kikötés a saját licencdokumentumában — ez tulajdonosi döntés, nem
merge-stratégia.

---

## A tizenkét lelet

Mind újramérve a `d649cca`-n, mielőtt issue lett belőle. Tizenegy lezárva.

| # | mit | hol |
|---|---|---|
| 27 | a hook fájltartalmat értékelt aritmetikaként — három sink | `hooks/context-monitor.sh` |
| 28 | a signer `curl -k`-ra váltott és úgy küldte a tokent | `git_hook_commit-msg.sh` |
| 29 | sorvégi komment elrejtette a futó jobot | `check-stale-jobs.sh` |
| 30 | sorvégi komment újranyitotta a #14 által zárt bypasst | `close-job.sh` |
| 31 | `envsubst` a teljes környezetet a promptba tágította | `run-job.sh` |
| 32 | validálatlan `JOB_ID` érte el az `rm -rf`-et | `run-job.sh` |
| 33 | a CI egy Python fájlt fordított; ~250 sor sosem került parserhez | `gate.yml` |
| 34 | a finalizer javított metát pusholt elavult index mellé | `run-job.sh` |
| 35 | a workflow-nak nem volt permissions, timeout, pinelt action | `gate.yml` |
| 36 | a doksi nem létező kapuszabályokat állított | `README.md`, `SPEC.md` |
| 37 | a §7(b) kikötés nem abban a fájlban volt, ami irányadó | `LICENSE.md` |
| 38 | két különböző fa azonos aláírást adott (submodule) | `git_hook_commit-msg.sh` — **nyitva** |

---

## Ami a kampány módszertani tanulsága

Minden javítás mutációval lett mérve: a védelem visszavéve, a suite újrafuttatva.
Hat esetben ez talált olyat, amit átnézés nem talált volna meg — két mutáció
zölden hagyta a suite-ot, mert exit code-ra mért és nem az elutasítás okára; egy
suite üres fájlon ment át; egy teszt beállt végtelen rekurzióval ahelyett, hogy
pirosat adott volna; és a checkerek maguk kétszer tévedtek.

Egy kapu, ami nem tud pirosat adni, díszítés. Egy teszt, ami beáll, még annyi
sem: nem mond semmit, csak elfogy tőle az idő.
