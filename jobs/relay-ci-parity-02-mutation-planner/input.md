# relay-ci-parity-02-mutation-planner — Rust mutánsfelsorolás fail-closed javítása és a mutációs tervező vakfoltjai

## Kontextus

A `CentralInfraCore/CIC_Relay` **#169** issue (másolat: `ref/issue-169-body.md`) tízlépéses
PR-sorozat. **Ez a job a PR-02-t fedi:** „Fix mutation planner and faulty measurement paths”,
záró feltétel: *minden felsorolási hiba fail-closed*.

A PR-01 (cic-factory #47, mergelve: `30ff4ad`) mért és dokumentált; annak jelentése az
alap, amire ez a job épül:

- `ref/pr01-gate-defect-repro.md` — a felsorolási kapuhiba reprodukciója (A/B/C eset).
- `ref/pr01-inventory-and-gap-analysis.md` — 4.2 szakasz (tervező-próbák P1–P9), 8. szakasz (PR-02 javaslat).

**Más, mint a PR-01:** ez a job **implementáció**. A CIC_Relay workflow-it és scriptjeit
módosítod, és **PR-t nyitsz a CIC_Relay felé** (lásd Git instrukciók). A workflow/CI
módosítására ebben a jobban kifejezett felhatalmazás van, de **csak a lenti scope-ra**.

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`,
   `limits` fogalmakra. A státuszt (implemented / scaffold / concept) node- vagy fájlszinten
   támaszd alá, különben ne állítsd tényként.
2. Olvasd el: `ref/issue-169-body.md`, `ref/pr01-gate-defect-repro.md`,
   a `ref/pr01-inventory-and-gap-analysis.md` 4.2 és 8. szakaszát.
3. Klónozd friss klónként a workspace-be: `$WORKSPACE/CIC_Relay/` (alapértelmezett ág
   `main`; a `devel` elavult) és `$WORKSPACE/cic-primitive-forms/` (csak olvasásra, referencia).
   **Rögzítsd a pontos commit-azonosítót és az ágat** mindkettőből; a PR-01 mérése a
   `bc2c4e0` Relay-commiton készült — ha a `main` azóta mozdult, írd le, mi változott a
   három érintett workflow-sorban és a `mutation_plan.py`-ban.
4. **Verifikáld újra a hibát a friss klónon**, mielőtt javítasz: a PR-01 reprodukciója
   (`ref/pr01-gate-defect-repro.md`, scriptek a `jobs/relay-ci-parity-01-inventory/output/raw/`
   alatt) még áll-e. Amit nem tudsz újra előidézni, azt ne javítsd „vakon”.
5. Reachability-szabály: egy scriptről csak akkor mondd, hogy a CI hívja, ha megvan a
   workflow `file:line`; egy Go szimbólumról csak hívási úttal (`grep … | grep -v _test.go`
   vagy `deadcode ./...`).

## Feladat

### A. Rust mutánsfelsorolás fail-closed (kötelező, először)

Érintett sorok a PR-01 szerint: `mutation-pr.yml:65`, `nightly.yml:146` és `:148`
(`n=$(cargo mutants … --list … | grep -c . || true)`).

- A felsorolás kimenete fájlba megy, a `cargo mutants` **kilépési kódját előbb** ellenőrizd;
  a darabszámot csak sikeres felsorolásból vedd.
- A jogosan üres felsorolás (A eset: érvényes diff, nincs mutálható kód) **külön, explicit
  ág**: `n=0` csak sikeres felsorolásból jöhet.
- Hibás felsorolás (B: olvashatatlan diff, C: hibás cargo-mutants konfig) **piros lépés**, nem
  `n=0`. Hiba esetén a `skipped` rust-job sem lehet a zöld kapu útja.
- A `|| true` eltávolítása önmagában és a `pipefail` önmagában **nem** javítás (a PR-01
  ellenpróbái szerint) — a javítás a kilépési kód explicit kezelése.
- Ugyanez a minta másutt is előfordulhat a `.github/workflows/` alatt: keresd meg
  (`grep -rn '|| true' .github/`), és minden találatnál döntsd el és írd le, mandatory
  gate része-e. A találatot csak akkor javítsd, ha a felsorolási hibaosztályba tartozik;
  a többit jelentsd.

**Negatív teszt (kötelező):** egy a CI-ban futó, a javítás előtti hibát **reprodukáló** teszt,
amely A-n zöld, B-n és C-n piros. A teszt a javítás nélküli workflow-szövegen **bukjon**
(ezt mérd le és add meg a kimenetét: a kapu ≠ hogy bukni tud).

### B. `mutation_plan.py` vakfoltjai (kötelező)

A PR-01 4.2 szakaszának próbái (P1–P9) alapján a tervező a teszt-, kapu-, függőség- és
build-változásra nem eszkalál, és törölt fájlra csendes. A #169 szerint a tesztváltozás
nem kezelhető „a mutációs eredményt nem érintő” változásként, és bizonytalan szűkítésnél
konzervatívan FULL-ra kell eszkalálni.

- Minden P1–P6, P8 vakfoltra: FULL-eszkaláció, vagy a módosított teszt által futtatott
  termékkód bevonása (Forms: `docs/DELTA-DIFF-GATE.md` §2.1–2.2 — referencia, nem másolandó).
- Törölt fájl (P2) nem lehet csendes.
- Az új csomag (P7) és az ismeretlen `--base` (P9) **működő** ellenőrzések: ne romoljanak el
  (regressziós teszt).
- Minden eseten negatív teszt, amely a PR-01-ben mért hibát reprodukálja a javítás előtt.
  Ha egy eset javítása döntést igényel (pl. a P5 `Cargo.toml` → hány mutáns, **PR-01-ben
  nem mért**), előbb mérd le, azután dönts, és írd le.
- A teszteket a repó meglévő script-tesztjeinek mintájára, a CI-ba kötve add hozzá.

## Nem része a jobnak (ne csináld)

- Küszöb vagy baseline lazítása; bármilyen kizárás a scope-ba tolva.
- Eszköz-verzió pin (`cargo-mutants`, `cargo-llvm-cov`, `GREMLINS_VERSION`) — külön döntés.
- Nightly horgony (`nightly_last_full`) és a `deadcode` lépés státusza — külön döntés;
  ha közben szükségesnek látod, **jelentsd**, ne változtasd.
- Shard-teljességi ellenőrzés (PR-03), ág-lefedettség (PR-04), seeded defects (PR-05),
  `verifyBuildHash` bekötése (termékkód, külön PR).
- Termékkód módosítása. Ha egy negatív teszt hiányzó termékgaranciát tár fel, rögzítsd, ne rejtsd.
- A CIC_Relay külső beállításainak (ruleset, branch protection, required check) módosítása.

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented. A workflow létezése ≠ hogy fut, és a kapu ≠ hogy bukni tud.
- Exit code 0 ≠ sikeres mérés. Üres kimenet ≠ nulla mutáns ≠ sikertelen felsorolás.
- Egy sikeres helyi futás ≠ hogy a CI-kapu hibás bemenetnél pirosra vált: ahol ezt állítod, mérd le.
- A teszt zöldje ≠ hogy a teszt bukni tud: a negatív tesztet a javítás nélküli állapoton is futtasd.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként.

## Verifikáció és bizonyítás

- Minden javítás mellé a **javítás előtti** és **utáni** futás nyers kimenete (parancs + kimenet).
- **Nem elég a helyi futás:** a #169 10. szabálya szerint egy CI-fázis csak akkor kész, ha
  GitHub Actions futás igazolja. A PR-on futó workflow **run id-ját és headSha-ját** vesd
  egybe a tesztelt committal; ha nem futott vagy nem mérhető, írd: **nem mérve**.
- A workflow-szöveg olvasata ≠ futás: ahol csak olvastad, mondd ki.
- Amit nem mértél, az **nem mérve**, nem becslés.
- Tervezz be egy ellenpróbát a negatív tesztre magára: a kapu bukjon a hibás (régi) formán.

## Output

A cic-factory klónban: `jobs/relay-ci-parity-02-mutation-planner/output/`

- `output/pr02-report.md` — magyarul: vizsgált commitok; mi változott a PR-01 óta; javítások
  soronként (előtte/utána); negatív tesztek és a bukásuk bizonyítéka; GitHub Actions run id-k;
  claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`);
  nyitott döntések; amit nem mértél.
- `output/raw/` — nyers kimenetek és mérőscriptek (minden `.sh` első sora `#!/usr/bin/env bash`,
  a gate ShellCheck-et fut).

A CIC_Relay módosítás a Relay-klónban, külön ágon, PR-ként (lásd lent).

## Definition of Done

- Mindkét repó commit-azonosítója és az ág leírva.
- A hibák újrareprodukálva a friss klónon, vagy kimondva, miért nem.
- A/B/C felsorolási eset: A zöld, B és C piros — mérve, nyers kimenettel.
- Minden P1–P6, P8 vakfolt kezelve vagy kimondottan indokolva, negatív teszttel; P7 és P9 nem romlott.
- A negatív tesztek a javítás nélküli állapoton bukása mérve.
- Valódi GitHub Actions run id a PR headSha-jára, vagy **nem mérve**.
- A CIC_Relay PR leírása pontosan azt állítja, ami mérve van.

## Git instrukciók

- **cic-factory:** commit és push **csak** a `feature/relay-ci-parity-02-mutation-planner`
  ágra. Main-re, devel-re nem pusholsz; merge-et nem csinálsz. A job `meta.yaml` státuszát
  nem módosítod (a tulajdonos zárja).
- **CIC_Relay:** külön ág (`feature/relay-ci-parity-02-mutation-planner`) a friss klónból,
  az alapértelmezett ág a `main`. PR-t a `main`-re nyiss (`--base main` explicit). Nem
  mergelsz. A PR **egy** témájú legyen: mutációs felsorolás + tervező; termékkód nincs.
- **Commit-üzenet:** nincs `Co-Authored-By` vagy AI-re utaló sor, sem a commitban, sem a PR
  leírásában. Vigyázz: a squash-merge a main-re trailert vihet — ezt jelezd a PR-ban,
  a merge módját a tulajdonos dönti.
- Friss klónban placeholder identitás lehet és nincs Vault-aláírás: ezt jelezd az outputban,
  az aláírást a tulajdonos pótolja.
- A `git push` hívást a tulajdonos futtathatja, ha a környezet a push-t elutasítja; ilyenkor
  add oda a pontos parancsot, ne kerüld meg.

## Nyelvi szabály

Dokumentáció magyarul. Parancsok, kód, YAML, shell angolul.
