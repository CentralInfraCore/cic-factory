# cic-factory-core v0.1.0

Az első kiadás. A `cic-factory`-ból history-megőrzéssel kiemelt mag, azóta a
lifecycle kikényszerítésével és hét viselkedési teszt-suite-tal.

Tag: `core/@v0.1.0`

---

## Mit tartalmaz

**A modell** — [`SPEC.md`](../SPEC.md): szerepek, job lifecycle, állapotgép, lease,
„git a bizalom forrása", a három gépi kapu.

**Az implementáció** — `tools/`: `run-job.sh`, `validate-spec.sh`,
`validate-output.sh`, `close-job.sh`, `check-stale-jobs.sh`, `update-index.sh`,
hook-telepítők és a commit-aláíró hook.

**A felület** — `.claude/commands/`: `job-create`, `job-validate`, `job-run`,
`job-review`, `job-close`, `job-boot`.

**A séma** — [`jobs/.schema/meta.yaml`](../jobs/.schema/meta.yaml), egyetlen
definícióban.

---

## Amit ez a verzió kikényszerít

| | |
|---|---|
| `agent_done ≠ done` | a `run-job.sh` gépileg nem tud `done`-t írni; az `awaiting_review → done` kizárólag a `close-job.sh` átmenete, C1–C5 feltételekkel |
| spec-kapu | a `run-job.sh` NO-GO specen nem indul; a `--skip-spec-gate` megkerüli, de `spec_gate: skipped`-et ír, és a C5 elutasítja a lezárást, amíg a `review.md` ezt nem ismeri el |
| lease | a `running` állapothoz határidő tartozik, ami a committal kimegy a remote-ra, tehát az elakadás a halott folyamat közreműködése nélkül eldönthető |
| egy séma | a `check-docs.sh` D2 elutasít minden dokumentumot, ami újradefiniálja a `meta.yaml`-t |
| licenc-láthatóság | minden forrásfájl SPDX-fejlécet hordoz; a kapu elutasítja azt, amelyik nem |

Minden kapu bukását szándékosan elrontott másolaton mérték, mielőtt bekerült.
Hét suite, **104 check**.

---

## Amit NEM garantál

Ez az őszinte fele, és fontosabb a fentinél.

- **Nincs end-to-end teszt.** Semmi nem futtat le egy teljes jobot. A kapuk azt
  bizonyítják, hogy az egyes döntések helyesek, nem azt, hogy a rendszer működik.
- **A `meta.yaml` sémája template, nincs mögötte validátor.** Az enumok
  kommentben élnek; egy elgépelt mezőnév némán elfogadódik.
  ([#9](https://github.com/CentralInfraCore/cic-factory-core/issues/9))
- **Az agent-hookok tanácsadók, nem policy-határ.** Regex a parancs-szövegen,
  ismert megkerülési utakkal.
  ([#10](https://github.com/CentralInfraCore/cic-factory-core/issues/10))
- **A `check-stale-jobs.sh`-t semmi nem futtatja magától.**
  ([#19](https://github.com/CentralInfraCore/cic-factory-core/issues/19))
- **A mag még CIC-kötött.** `cic-graph`, `kb_focus`, `$CIC_*`,
  `~/.claude-personal` — a teljes, mért lista a
  [README](../README.md#known-coupling--what-round-two-has-to-break)-ben. Ez a
  kiadás a *jelenlegi állapotot* rögzíti, nem egy általánosított API-t.

Aki erre épít, a fenti öt ponttal együtt épít rá.

---

## Kompatibilitás

Nincs mihez képest — ez az első kiadás. A `meta.yaml` viszont **három új mezőt**
kapott a kiemelés óta:

| mező | mit |
|---|---|
| `spec_gate` | `passed` \| `skipped` — a `run-job.sh` írja minden futáson |
| `lease_expires` | a `running` állapot határideje |
| `usage` | költség, turn-szám, tokenek |

A `promptmap_ref` **kikerült**: nem létező fájlra mutatott.

A kiemelés előtti jobok metája egyik új mezőt sem tartalmazza. Ez nem hiba: a
`close-job.sh` üres `spec_gate` esetén figyelmeztet és átenged, a
`check-stale-jobs.sh` pedig „nem eldönthető"-ként jelenti őket. Elakadtnak
jelölni hamis riasztás lenne, elhallgatni pedig azt sugallná, hogy ellenőrizve
vannak.

---

## Átvétel a cic-factory-ba

A propagáció `git remote` + merge egy release tagről. Lemérve: **egy konfliktus**
(`README.md`), és három fájl érkezne újként (`gate.yml`, `LICENSE`,
`LICENSE.md`).

A `cic-factory`-nak kell a `.gitattributes`-ba:

```
CLAUDE.md merge=ours
```

plusz egyszer `git config merge.ours.driver true`. Mindkét repónak van
`CLAUDE.md`-je, szándékosan más tartalommal — enélkül minden release-merge
ütközne rajta.

**A fájdalom egyszeri:** az első `--allow-unrelated-histories` merge után van
közös ős, onnantól minden további release-merge közönséges merge.
