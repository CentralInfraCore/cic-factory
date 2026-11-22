# relay-ci-parity-06n-attempt-binding — a PK-olvasó futási kísérlethez kötése (CIC_Relay #212, 11. lépés)

## Kontextus

A #85 (06m, 4.6b csomag) mergelve (7d83465), a csomag az X repón (`CIC-Security-Lab/ci-adversarial-lab`) a `3c1eabea…` fejen. Az első PK-futás (45045309607) **1. kísérlete** `action_required` lett, 0 jobbal: a GitHub a `pk-canary-channels.yml`-t gyanúsként jelölte, jóváhagyásig nem futtatta (mért megfigyelés, az ok nem ismert). A tulajdonos webes jóváhagyása ugyanazon futásazonosítón **2. kísérletet** hozott létre (`success`, job `pk-channels` `success`). A 06m olvasója és letöltője a `run_attempt == 1` értéket kódolva követeli, ezért a fail-closed módon elutasította a 2. kísérletet. Tulajdonosi döntés (a tulajdonos szövege szerint): 06n javítócsomag APPROVE, K-5 kísérletenként számolva (5/300), új PK-futás nem szükséges.

## Hatókör

**Kizárólag a harness javítása** (`read-pk.py`, `fetch-pk.sh`) és a hozzá tartozó leírás. A 06m tartalma nem módosul (a javított harness új job alatt él, a 06m a történeti állapot). Nem hajtok végre semmit az X repón, nem indítok futást, nem töltök le bizonyítékot. A letöltés és kiolvasás a javítás mergelése után a tulajdonosé.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06m-measurement-workflow-package/output/harness/read-pk.py`, `fetch-pk.sh` (a javítandó, mergelt változat)
- `jobs/relay-ci-parity-06m-measurement-workflow-package/output/measurement-workflow-package.md` (4. szakasz: futáshoz kötés)

## Követelmények

- Kötelező, független `--expect-attempt` bemenet az olvasónak; hiánya `INCOMPLETE`.
- A letöltés és a manifest ugyanahhoz a kísérlethez kötött (a kísérlet-specifikus API végpontok: `runs/ID/attempts/N`, `.../jobs`, napló `--attempt N`).
- A korábbi kísérletek állapotának rögzítése a manifestben.
- (review F1) A letöltés a futás aktuális kísérletét a gyűjtés előtt és után is ellenőrzi; az artifact egyedi azonosítóval választott (a kísérlet időablakán belül létrehozott egyetlen), a manifest rögzíti az azonosítót és az eredet adatait; bizonytalan eredet esetén fail-closed.
- (review F2) A manuálisan csatolt összegzéshez a tulajdonos explicit kísérletszámot ad; az olvasó egyezteti a manifesttel és az `--expect-attempt` értékével; a manuális eredet jelölése megmarad.
- (review F3) A diagnosztikai üzenet a tényleges kísérletszámot írja.
- A 2. kísérlet elfogadásának további feltétele: az 1. kísérlet `completed` / `action_required`, nulla jobbal. 3. vagy későbbi kísérlet nem fogadható el.
- Negatív tesztek minden új elfogadási feltételre; a többi integritásellenőrzés (futásazonosító, repó, head SHA, digest, csatornák) változatlan.

## Elfogadhatatlan rövidítések

- NEM fogadható el: a `run_attempt == 1` követelmény egyszerű átírása `2`-re vagy kikapcsolása; a kísérlet független tulajdonosi bemenet.
- NEM fogadható el: a 2. kísérlet elfogadása a korábbi kísérlet állapotának ellenőrzése nélkül.
- NEM fogadható el: az olvasó, amely nem tud bukni; az önteszt beültetett hibák nélkül nem bizonyíték.
- NEM fogadható el: a javítás megléte ≠ működik, és a PK teljesülése ≠ sikeres önteszt; a nyers bizonyítékot a tulajdonos tölti le és olvastatja ki a javítás mergelése után.
- NEM fogadható el: bármilyen írási művelet az X repón vagy az éles szervezetben; hitelesítő adat átadása nekem.

## Output

- `output/attempt-binding.md` — a változás leírása, a megfigyelés (mért), a K-5 számlálás, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)
- `output/harness/read-pk.py`, `output/harness/fetch-pk.sh` — a javított harness

## Git

Feature branch `feature/relay-ci-parity-06n-attempt-binding`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
