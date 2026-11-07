Kész. Összefoglaló:

## Mi volt kész, mi maradt

A workspace `input.md`-je elején az orchestrátor **szűkített folytatási hatókört** hagyott, ami felülírja az eredeti Definition of Done-t. Eszerint:

- **Kész és immutable bemenet:** `baseline.md` (74 kB), `contract-mapping.md` (33 kB) — hash-elve, nem módosíthatók.
- **Hátra volt:** `relay-requirements.md`, `claim-evidence.md`.
- `agent-output.md` csak a limit-üzenetet tartalmazta (60 bájt).

## Amit most elkészítettem

| Fájl | Sor | Tartalom |
|---|---|---|
| `relay-requirements.md` | 627 | **R1** op-szókészlet 4 vs 8 (a csatlakozási mechanizmus kimondottan *nincs eldöntve*) · **R2** tartós CIC `uid` → OCID kötés · **R3** Forms production bekötés · **M1** létrejött `resource_id` · **M2** `compartment_id` binding (`PROPOSED / OWNER DECISION REQUIRED`) · **M3** production `Observe` rés + a kötelező blokkoló negatív teszt. Mindegyik: `fájl:sor`, jelenlegi/kívánt viselkedés, negatív teszt, elfogadási feltétel, háromszintű státusz, bizonyíték-osztály |
| `claim-evidence.md` | 261 | 144 normatív-oszlopos állítás-sor, mindegyik `AGENT_MEASURED` (eszközfuttatás vagy kódolvasás) / `ORCHESTRATOR_VERIFIED` / `DOCUMENTED` / `NOT MEASURED` / `NOT INDEPENDENTLY VERIFIED` osztállyal |
| `agent-output-resume-2026-11-07.md` | 236 | a kötelező beszámoló-kérdések + a hatókör-kényszerek tételes elszámolása |

Új bizonyítékot csak **olvasással** gyűjtöttem — nem futtattam új Docker-, Go-, mutációs vagy lefedettségi mérést.

## Négy korrekciót átvettem az orchestrátor újraméréseiből

A két kész dokumentum immutable, ezért ezek a `claim-evidence.md`-ben élnek:

1. **Sorlefedettség: 82,7%, nem 82,9%** — az én számom nem reprodukált, az eltérés az én mérésemben volt.
2. **Tesztszám: 55 + 7 manuális**, nem 26 + 8 — a számolási szabályt nem mondtam ki.
3. **A licenc-ellentmondás oka más:** a `forms-integration-direction.md:90` „vegyes licenc" mondata a *cic-factory* licencét írja le, nem a Formsét. (A Forms Apache-2.0 megállapítása megerősítve; javító PR `#35`.)
4. **„Implemented a registryben" pontosítva:** a correspondence applierének nincs production hívója — implementált + tesztelt, de nem használt.

## Státusz: PARTIAL, nem GO

Hat tétel `NOT INDEPENDENTLY VERIFIED` (lefedettség, tesztszám, mutáció `HOLD`-on, `govulncheck`, Q3/Q6/Q9), két kérdés tulajdonosi döntésre vár (`compartmentId` eredete, R1 mechanizmusa), és a `validate-output.sh` a push-tilalom miatt nem futott az előírt helyen.

A legkisebb következő lépés igazolt alapon: **M3** — a production `Observe` negatív tesztje. Mért ok: a garancia egyetlen teszteletlen őrfeltételen áll (`correspondence.go:63-66`), és az orchestrátor telepített hibája szerint annak eltávolítása után minden teszt zöld marad.

## Git

Lokális, Vault-aláírt commit `b62f624` a `feature/forms-oracle-provider-integration-01a` ágon, csak a három konkrét fájl (`git add -A` nem volt). **Push nem történt** — a hatókör 8. kényszere ezt kimondottan megtiltja és felülírja az `input.md` git-szakaszát. A `baseline.md`/`contract-mapping.md` hash-e a commit után is változatlan.

Egy dolgot jelzek, mert nem az én hatáskörömben van: **`baseline.md` és `contract-mapping.md` még mindig nem követett fájl** (`??`) — a megszakadt futás nem commitolta őket. Nem vettem fel git-be, mert a hatókör bemenetként, nem munkatételként jelöli őket; de a feature branch ma nélkülük is pushol­ható lenne.