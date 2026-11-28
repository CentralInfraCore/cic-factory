# SS-03: a `poll` és a `create` kérés eltérésleírása (nem szerződés-módosítás)

**Státusz:** célzott eltérésleírás a tulajdonosi döntéshez. **A befagyasztott SS-03 nem módosul.** A jelenlegi `POLICY_PATH` elutasítás nem implementációs hiba, ha a kérés a szerződésen kívül esik.

| Kérdés | `poll` | `create` |
|---|---|---|
| Milyen tényleges provider request szükséges? | `GET /<api-verzió>/workRequests/<work-request-OCID>` (a modul `pollTargetPath`: pontosan ez az alak, a kérés `work_request_id`-ből vagy a legacy `path`-ból) | `POST /<api-verzió>/<gyűjtemény>` a létrehozandó erőforrás törzsével; **még nincs `resource_id`**, az a válaszban jön létre |
| Milyen effect és authorization tartozik hozzá? | `external-read` (egy Work Request olvasása); a megfigyelési profil `GET` módszere alatt engedélyezhető lenne | `external-write`; a megfigyelési profil `ObservationOnly` szabálya a `POST`-ot **tilos**; az authorization és a binding a létrehozott erőforráson még nem létezik |
| Miért nem fejezhető ki a jelenlegi SS-03 szerint? | az SS-03 a kérés útvonalát a policy `path_template`-jébe behelyettesített `resource_id`-val **pontosan** egyezteti; a Work Request útvonal más erőforrástípus (`workRequests`), és a hozzá tartozó binding nincs a policyban | a `resource_id` és a binding digest kötelező az SS-03-ban, create-nél nem létezik; ráadásul a `POST` a megfigyelési profilban tiltott |
| Szükséges-e az eredeti megfigyelési PoC-hoz? | **nem**: a poll csak aszinkron írás (create/update/delete) utáni Work Request követéshez kell; a megfigyelési PoC nem ír | **nem**: a megfigyelési PoC nem hoz létre erőforrást |

**Következtetés (javaslat a tulajdonosnak):** a megfigyelési PoC-hoz **egyik sem kell**, ezért az SS-03-ot **nem bővítem**. A modul `poll` és `create` hívásai a Relay-n **`POLICY_PATH` / `POLICY_METHOD` elutasítást** kapnak, és a WP-04b ezt **célzott negatív teszttel** rögzíti (nem elfedi). Ha később egy írási PoC kellene: a `poll` egy külön, `external-read` hatású operációként, saját útvonal-sablonnal és saját binding-típussal vezethető be (kis, ellenőrizhető kiterjesztés); a `create` külön szerződés (hatás: write, authorization: operátori jóváhagyás, binding: a célgyűjtemény), amely nem része a mostani PoC-nak.
