# CLAUDE.md

Guidance for Claude Code when working **on this repository**.

Ha azt keresed, *mit csinál* a factory — a lifecycle, a kapuk, a job-struktúra —,
az a [`SPEC.md`](SPEC.md)-ben van. Ez a fájl arról szól, hogyan kell ezen a
repón dolgozni.

---

## Mi ez a repo

A `cic-factory-core` az agent factory újrahasznosítható magja: job lifecycle,
gépi kapuk, agent-futtató eszközök. A
[`cic-factory`](https://github.com/CentralInfraCore/cic-factory)-ból lett
kiemelve, a történet megőrzésével.

A felosztás egy kérdés repónként:

| repo | milyen kérdésre felel |
|---|---|
| `cic-factory-core` | mit tud a gyár általánosan? |
| `cic-factory` | hogyan használja ezt a CIC? |

Ha CIC-specifikus dolgot akarnál ide írni — ökoszisztéma-térkép, konkrét repo
path, MCP szerver, CIC-döntések —, az a `cic-factory` `CLAUDE.md`-jébe való.

---

## Nyelvi szabály

- Dokumentáció, Claude-utasítások, agent promptok: **magyarul**
- Forráskód, YAML, JSON, shell script, változónevek, kódon belüli komment: **angolul**
- **GitHub-felület** — issue, PR cím és leírás: **angolul**

---

## Kapu és tesztek

A `main` védett; a `gate` check kötelező, `enforce_admins` bekapcsolva. Minden
változás PR-en megy.

A kapu hat viselkedési suite-ot futtat a parse- és shellcheck-lépéseken felül:

| suite | mit fed |
|---|---|
| `tools/test-run-job-finalizer.sh` | a finalizer trap: SIGPIPE, SIGTERM, zárt stdout |
| `tools/test-lifecycle-transitions.sh` | a `run-job.sh` állapotátmenete és az invariáns, hogy nem írhat `done`-t |
| `tools/test-close-job.sh` | a `close-job.sh` összes elutasítása (C1–C5) |
| `tools/test-run-job-spec-gate.sh` | a spec-kapu és az auditálható menekülőút |
| `tools/test-install-claude-hooks.sh` | a hook-installer konvergál-e |
| `tools/test-stale-jobs.sh` | az elakadt `running` felismerése |

### A szabály, ami ezeket összetartja

**Egy kapu, ami nem tud pirosra váltani, dekoráció.** Mielőtt bármilyen
ellenőrzés bekerül, le kell mérni, hogy egy szándékosan elrontott másolaton
tényleg bukik-e.

Ez nem formaság. Ebben a repóban eddig a következők derültek ki *csak azért*,
mert valaki lemérte:

- a finalizer suite **15/15-öt adott** egy `run-job.sh`-ra, amit visszaszabotáltak
  `done`-ra — strukturálisan vak volt rá
- egy `[[ -f ]]` ellenőrzés kivétele észrevétlen maradt, mert a következő sor
  `[[ -s ]]`-e is elutasított, csak más indokkal → **az indokot is mérni kell**
- a `close-job.sh` `awk -F'"'` parsere az idézőjel nélküli értéket üresnek
  olvasta → **két karakter törlése kikapcsolta volna a C5-öt**
- a spec-kapu suite helyben zöld volt, CI-ban **7/8 FAIL**, mert a fejlesztő
  gépén létezett egy agent-könyvtár → **a helyi zöld nem bizonyíték**
- egy szabotázs-próba némán nem alkalmazódott, és „a suite vak" eredményt adott
  → **a próba előbb igazolja, hogy a szabotázs landolt**

Amit egy ellenőrzés nem bizonyít, azt ne állítsd róla — sem a kódban, sem a
README-ben, sem a PR-ben.

---

## Licenc

AGPL-3.0-or-later, §7(b) attribution kikötéssel. Minden forrásfájl SPDX-fejlécet
hordoz, és a kapu elutasítja azt, amelyik nem. Két fájl a `tools/hooks/` alatt
MIT — lásd [`LICENSE.md`](LICENSE.md).
