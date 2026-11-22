# #212 — A PK-olvasó futási kísérlethez kötése (06n, a 06m javítása)

**Státusz: javítás (helyi, mért öntesztekkel).** A 06m (#85) harnessét javítja; a 06m tartalma nem módosul. A javított olvasó a bizonyítékot még **nem** értékelte: a nyers bizonyítékot a tulajdonos a javítás mergelése után tölti le és olvastatja ki. A javítás megléte ≠ a PK teljesült. A mérések, a valódi kulcsműveletek és a Relay-implementáció HOLD.

## 1. A megfigyelés (mért, olvasott, labor X repó)

Az első PK-futás (45045309607, `workflow_dispatch`, `headSha` `3c1eabea…`):

| Kísérlet | Állapot | Job | Időpont (UTC) |
|---|---|---|---|
| 1 | `completed` / `action_required` | 0 | 16:42:14–16:42:16 |
| 2 | `completed` / `success` | `pk-channels` `success` | 17:08:31–17:08:47 |

A GitHub a `pk-canary-channels.yml`-t gyanúsként jelölte, jóváhagyásig nem futtatta (a tulajdonos szövege szerint: „GitHub detected that this workflow file may be malicious. It will not run until someone with write access approves it."). **Az ok nem ismert** (a fájl titokkezelő elemei csak következtetett jelöltek, nem mért). A tulajdonos webes jóváhagyása **ugyanazon futásazonosítón 2. kísérletet** hozott létre. Következmény: **a bizonyíték azonosításához a futásazonosító önmagában nem elég**, a kísérlet is kell. A 06m olvasója a `run_attempt == 1` értéket kódolva követelte, ezért fail-closed elutasította a 2. kísérletet.

## 2. A változás

| Elem | 06m | 06n |
|---|---|---|
| Kísérlet | kódolt `1` | **kötelező, független `--expect-attempt`**; hiánya `INCOMPLETE`, eltérése `NOT MET` |
| Elfogadott kísérletek | csak 1 | 1 (korábbi kísérlet nélkül), vagy 2, **ha az 1. `completed` / `action_required` és nulla jobos volt**; 3. vagy későbbi nem |
| Letöltés | `runs/ID`, `--log` | `runs/ID/attempts/N`, `.../attempts/N/jobs`, `--attempt N`; a `fetch-pk.sh` 4. paramétere a kísérlet |
| Manifest | futás, repó, head, fájl-digestek | + **`previous_attempts`** (kísérlet, állapot, következtetés, jobszám), az olvasó minden értékeléskor újraellenőrzi |
| Többi ellenőrzés | | változatlan: futásazonosító, repó, head SHA, digest, csatornák, kanári-ellenőrzés |

A kísérlet független tulajdonosi bemenet, nem a manifestből átvett érték: a `run_attempt` átírása `2`-re önmagában nem fogadható el.

## 3. Ellenőrzés (helyi, 2026-11-22)

```bash
python3 -I jobs/relay-ci-parity-06n-attempt-binding/output/harness/read-pk.py --selftest
```

**72 eset, mind a várt eredménnyel.** Új esetek (a 06m 54 esetéhez képest): a 2. kísérlet elfogadása tartott 1. kísérlet után; az 1. kísérlet hiányzó, sikertelen, jobos, nem befejezett vagy sikeres története; a manifest és a tulajdonos kísérlete eltér mindkét irányban; 3. kísérlet; 1. kísérlet korábbi kísérlettel; hiányzó és nem numerikus `--expect-attempt`; a manifest-író 15 esete (köztük 2. kísérlet története nélkül, jobos 1. kísérlet, a futás 1, a tulajdonos 2, 3. kísérlet, nem numerikus kísérlet). A `fetch-pk.sh` valódi GitHub-hívásait nem futtattam, csak szintaxist ellenőriztem és a korábbi kísérletek JSON-összeállítását egy példán; a végpontok (`runs/ID/attempts/N`, `.../jobs`) olvasása a labor futásán megtörtént.

## 4. K-5 számlálás (tulajdonosi döntés, a tulajdonos szövege szerint)

Kísérletenként, konzervatívan: egyedi workflow-futás 4 (1 PR-futás, 1 push-futás, 1 bootstrap, 1 PK), futási kísérlet **5**, felhasznált keret **5/300**, fennmaradó **295**. Ez a szabály a további mérésekre egységesen érvényes.

## 5. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A webes jóváhagyás ugyanazon run ID alatt új kísérletet hozott létre | mért (olvasott, labor) | 1. szakasz táblázata, `runs/45045309607/attempts/{1,2}` | API-olvasás | a szabály általánosítása más esetre nem mért |
| A GitHub a workflow-t gyanúsként jelölte | mért (a tulajdonos által másolt banner) | a tulajdonos szövege | a tulajdonos másolata | az ok nem ismert |
| Az olvasó a kísérletet független bemenetként köti | mért (helyi) | 72/72 önteszt, a kísérlet-esetek | `read-pk.py --selftest` | a fetch-pk.sh valódi lánc nem futott a javítás óta |
| A 2. kísérlet csak tartott 1. kísérlet után fogadható el | mért (helyi) | a história-esetek elutasítva | `--selftest` | a „tartott" feltétel az 1. kísérlet megfigyelt állapotára épül; más tartás-ok nem fedettek |
| A letöltés a kísérletek végpontjait használja | olvasott (végpont), helyi szintaxis | `runs/ID/attempts/N` olvasása | `bash -n`, API-olvasás | a teljes lánc a valódi futáson még nem mért |
| A PK teljesült | **nem állítom** | — | a javítás mergelése után a tulajdonos által letöltött bizonyíték kiolvasása | a naplóformátum feltételezett |
| Az X vagy az éles szervezet módosult | nem | nincs ilyen parancs | `git log` | — |

## 6. Mit nem állít ez a dokumentum

- **Nem állítja,** hogy a PK teljesült vagy bukott; a bizonyítékot nem töltöttem le és nem értékeltem.
- **Nem állítja** a jelölés okát; az **nem ismert**.
- **Nem tartalmaz** H1/H2 mérést, K1/K2 használatot, kulcsműveletet, App-kulcsot vagy Relay-implementációt; ezek HOLD.
- **Nem módosítja** a 06m tartalmát és a #82–#85 döntéseit; a K-5 számlálási szabályt a tulajdonos szövege szerint rögzíti.
