# #212 — Az `--attach-summary` parancssori hívásának javítása (06o)

**Státusz: javítás (helyi, mért).** A 06n harnessét javítja, a 06n tartalma nem módosul. A PK még nem teljesült: a job-összegzés csatolása és kiolvasása a javítás mergelése után a tulajdonos által kimásolt összegzéssel történik.

## 1. A hiba (mért, a valódi hívásban)

A tulajdonos futtatása: `pk-run-212.sh read 45045309607 2 <összegzés>` → `read-pk.py --attach-summary` → `TypeError: attach_summary() missing 1 required positional argument: 'attempt'`. A `main()` az `attach_summary(args[1], args[2], args[3])` hívást használta, a #86 (F2) óta a függvény 4. paramétere a kísérlet. A hiba a #86-os változásom következménye. A selftest a függvényt közvetlenül hívta, ezért nem látta; a review és a CI sem tudta. A bizonyíték könyvtára sértetlen (`manifest.json` `summary: null`, nincs `summary.txt`). Külön megjegyzés: a futtatott parancsban a `/path/summary-copy.txt` a dokumentum példa-útvonala volt, nem létező fájl.

## 2. A javítás

`attach_summary(*args[1:])`, plusz **parancssori szintű tesztek** a selftestben (alfolyamat-hívás `python3 -I read-pk.py …`): `--attach-summary` (hiányzó kísérlet, hibás kísérlet, nem létező fájl, helyes hívás), az értékelő a csatolás után (`PK MET`, kilépési kód 0) és `--expect-attempt` nélkül (kilépési kód 1), `--check-run`, `--pick-artifact`, `--write-manifest` (helyes és hiányzó argumentum). Az indítószkript (`pk-run-212.sh`) a nem létező összegzés-fájlt a csatolás előtt elutasítja (a szkript a repón kívül él, nem része ennek a PR-nak).

## 3. Ellenőrzés (helyi, 2026-11-22)

```bash
python3 -I jobs/relay-ci-parity-06o-attach-summary-cli/output/harness/read-pk.py --selftest
python3 -I jobs/relay-ci-parity-06o-attach-summary-cli/output/harness/test-fetch-pk.py
```

**113 ellenőrzés a selftestben** (101 + 12 parancssori), a lánc-teszt 25. **Tud bukni:** a hibás sort egy ideiglenes másolatban visszaállítva a selftest elbukik (4 parancssori eset, kilépési kód 1).

## 4. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Az `--attach-summary` parancssori hívása működik | mért (helyi, alfolyamat) | a parancssori esetek helyes hívása `0`, utána az értékelő `PK MET` | `read-pk.py --selftest` | a valódi összegzés csatolása még nem történt meg |
| A parancssori belépési pontok tesztelt | mért (helyi) | 12 parancssori eset | `--selftest` | a `pk-run-212.sh` burkoló szkript a repón kívül él, nem tesztelt a CI-ben |
| A teszt tud bukni | mért (helyi) | a hibás sorral a selftest `FAILED`, kilépési kód 1 | a hibás sor visszaállítása ideiglenes másolatban | — |
| A bizonyíték sértetlen | olvasott | `manifest.json` `summary: null`, nincs `summary.txt` | `ls`, manifest-olvasás | a tulajdonos könyvtára, helyi |
| A PK teljesült | **nem állítom** | — | az összegzés csatolása és kiolvasása a javítás mergelése után | az összegzés csatornát csak a tulajdonos tanúsítása köti |
| Az X vagy az éles szervezet módosult | nem | nincs ilyen parancs | `git log` | — |
