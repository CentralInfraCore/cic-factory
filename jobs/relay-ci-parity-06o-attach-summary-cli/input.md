# relay-ci-parity-06o-attach-summary-cli — az `--attach-summary` parancssori hívásának javítása (CIC_Relay #212, 12. lépés)

## Kontextus

A #86 (06n) mergelve (31fbded). A meglévő PK-bizonyíték letöltése és kiolvasása működött a valódi GitHub-adatokon (futás 45045309607, 2. kísérlet; minden csatorna `MET`, az összegzés `NOT-READ`). A job-összegzés csatolásakor a `read-pk.py --attach-summary` parancssori ága `TypeError`-ral elbukott: a `main()` az `attach_summary()`-t 3 argumentummal hívta, miközben a #86 óta 4-et vár (a kísérletszám is). A selftest a függvényt közvetlenül hívta, a parancssori belépési pontot nem, ezért a hiba a review-n és a CI-n átment. A bizonyíték könyvtára sértetlen, nincs félig csatolt állapot.

## Hatókör

**Kizárólag az a hiba és a hozzá tartozó parancssori tesztek.** Nincs új futás, nem módosul az X repó, a bizonyítékot nem töltöm le újra. A javított harness új job alatt él (a 06n a történeti állapot).

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06n-attempt-binding/output/harness/read-pk.py`, `fetch-pk.sh`, `test-fetch-pk.py` (a javítandó, mergelt változat)

## Követelmények

- Az `--attach-summary DIR FILE RUN_ID ATTEMPT` parancssori hívás működik.
- Az összes parancssori belépési pont (`--attach-summary`, `--write-manifest`, `--check-run`, `--pick-artifact`, az értékelő) **tényleges alfolyamat-hívással** tesztelt: helyes hívás, hiányzó argumentum, hibás érték.
- Az összes belépési ponton helyes hívás, hiányzó argumentum és **hibás érték** is tesztelt; a 2. kísérlet csatolása teljes alfolyamat-hívással.
- Az `--selftest` kizárólag önálló hívásként elfogadott: más argumentummal kevert hívás elutasított, és nem helyettesíti a kért műveletet.
- A teszt tud bukni: a hibás sorral visszaállított változaton a selftest elbukik.

## Elfogadhatatlan rövidítések

- NEM fogadható el: a függvény közvetlen hívásának tesztje ≠ a parancssori belépési pont tesztje; a selftest zöldje ≠ működik a szkript a valódi hívásban, és a zöld teszt ≠ sikeres parancssori hívás.
- NEM fogadható el: a javított olvasó kimenetének elfogadása a valódi összegzés csatolása nélkül; a PK ítélet a javítás mergelése után, a tulajdonos által kimásolt összegzéssel készül.
- NEM fogadható el: új PK-futás, vagy a meglévő bizonyíték újraletöltése; írási művelet az X repón vagy az éles szervezetben.

## Output

- `output/attach-summary-cli.md` — a hiba, a javítás, a tesztek, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)
- `output/harness/read-pk.py`, `output/harness/fetch-pk.sh`, `output/harness/test-fetch-pk.py`

## Git

Feature branch `feature/relay-ci-parity-06o-attach-summary-cli`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
