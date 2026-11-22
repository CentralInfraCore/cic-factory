# #212 — Az `--attach-summary` parancssori hívásának javítása (06o)

**Státusz: javítás (helyi, mért).** A 06n harnessét javítja, a 06n tartalma nem módosul. A PK még nem teljesült: a job-összegzés csatolása és kiolvasása a javítás mergelése után a tulajdonos által kimásolt összegzéssel történik.

## 1. A hiba (mért, a valódi hívásban)

A tulajdonos futtatása: `pk-run-212.sh read 45045309607 2 <összegzés>` → `read-pk.py --attach-summary` → `TypeError: attach_summary() missing 1 required positional argument: 'attempt'`. A `main()` az `attach_summary(args[1], args[2], args[3])` hívást használta, a #86 (F2) óta a függvény 4. paramétere a kísérlet. A hiba a #86-os változásom következménye. A selftest a függvényt közvetlenül hívta, ezért nem látta; a review és a CI sem tudta. A bizonyíték könyvtára sértetlen: a `manifest.json`-ban **nincs `summary` kulcs** (olvasással ellenőrizve: `'summary' in manifest` hamis, a fájlban a `"summary"` szöveg 0 előfordulású), nincs `summary.txt`. (Az első kiolvasás `None` értéke a `m.get('summary')` hívás eredménye volt, nem tárolt `null`; a csatolás ellenőrzése a kulcs meglétét vizsgálja, ezért a javított csatolás nem utasítja el.) Külön megjegyzés: a futtatott parancsban a `/path/summary-copy.txt` a dokumentum példa-útvonala volt, nem létező fájl.

## 2. A javítás

`attach_summary(*args[1:])`, plusz **parancssori szintű tesztek** a selftestben (alfolyamat-hívás `python3 -I read-pk.py …`), minden belépési ponton **helyes hívás / hiányzó argumentum / hibás érték** mátrixban: `--attach-summary` (hiányzó kísérlet, hibás kísérlet, nem létező fájl, helyes hívás, a **2. kísérlet teljes alfolyamat-láncban**: csatolás 1-gyel elutasítva, 2-vel elfogadva, kiolvasás `PK MET`, rossz elvárt kísérlettel `NOT MET`); `--check-run` (rossz head, nem SHA, rossz repó, nem numerikus kísérlet, 2. kísérlet előzmény nélkül, hibás JSON, hiányzó fájl); `--pick-artifact` (rossz head, hibás lista, nincs artifact, hiányzó fájl); `--write-manifest` (rossz head, nem numerikus kísérlet, hibás zip-digest, hibás előzmény- és artifact-fájl; minden elutasításnál nincs manifest); az értékelő (rossz digest, hibás digest, rossz futásazonosító, nem numerikus futásazonosító, rossz kísérlet, rossz repó, rossz head, érték nélküli kapcsoló, felesleges pozicionális argumentum, nem létező könyvtár). **(Review F2)** az `--selftest` kizárólag önálló hívásként elfogadott: más argumentummal kevert hívás kilépési kód 2 (három negatív parancssori teszt); az öntesztbe rekurzió-védő került, hogy egy hibás `main()` ne végtelen alfolyamat-láncot, hanem tiszta `FAIL`-t adjon. Az indítószkript Az indítószkript (`pk-run-212.sh`) a nem létező összegzés-fájlt a csatolás előtt elutasítja (a szkript a repón kívül él, nem része ennek a PR-nak; **technikai adósság:** a későbbi reprodukálhatóság érdekében a repóba emelendő, külön döntéssel).

## 3. Ellenőrzés (helyi, 2026-11-22)

```bash
python3 -I jobs/relay-ci-parity-06o-attach-summary-cli/output/harness/read-pk.py --selftest
python3 -I jobs/relay-ci-parity-06o-attach-summary-cli/output/harness/test-fetch-pk.py
```

**151 ellenőrzés a selftestben** (101 függvényszintű + 50 parancssori), a lánc-teszt 25. **Tud bukni:** (a) a hibás `attach_summary` sort ideiglenes másolatban visszaállítva a selftest elbukik (4 parancssori eset, kilépési kód 1); (b) az `--selftest` önállóságának ellenőrzését kivéve a selftest elbukik (3 parancssori eset `got=99`, kilépési kód 1).

## 4. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Az `--attach-summary` parancssori hívása működik | mért (helyi, alfolyamat) | a parancssori esetek helyes hívása `0`, utána az értékelő `PK MET` | `read-pk.py --selftest` | a valódi összegzés csatolása még nem történt meg |
| A parancssori belépési pontok tesztelt (helyes hívás, hiányzó argumentum, hibás érték) | mért (helyi) | 50 parancssori eset, mind az 5 belépési pontra, a 2. kísérlet teljes láncával | `--selftest` | a `pk-run-212.sh` burkoló szkript a repón kívül él, nem tesztelt a CI-ben |
| A teszt tud bukni | mért (helyi) | a hibás `attach_summary` sorral és az `--selftest` önállósági ellenőrzés nélkül a selftest `FAILED`, kilépési kód 1 | a javítás visszavonása ideiglenes másolatban | — |
| Az `--selftest` nem helyettesíti a kért műveletet | mért (helyi) | kevert hívás kilépési kód 2, három negatív teszt | `--selftest` | — |
| A bizonyíték sértetlen, a manifestben nincs `summary` kulcs | olvasott | `'summary' in manifest` hamis, 0 előfordulás a fájlban, nincs `summary.txt` | `python3` manifest-olvasás, `grep -c`, `ls` | a tulajdonos könyvtára, helyi |
| A PK teljesült | **nem állítom** | — | az összegzés csatolása és kiolvasása a javítás mergelése után | az összegzés csatornát csak a tulajdonos tanúsítása köti |
| Az X vagy az éles szervezet módosult | nem | nincs ilyen parancs | `git log` | — |
