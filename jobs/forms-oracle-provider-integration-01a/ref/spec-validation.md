# Spec-validáció: jobs/forms-oracle-provider-integration-01a/input.md

Dátum: 2026-11-07 (a javított változat). Futtatta: a workdir orchestrátor, a job indítása **nélkül**. A job státusza: `pending`.

**Javítás az előző változathoz képest.** Az első változat K11-indoklása **hamis volt**: azt állította, hogy az `input.md` előírja az agentnek a KB-keresést, és hogy egyetlen id sem volt igazolható. Az `input.md`-nek akkor nem volt Boot sequence szakasza, és az id-kat nem kerestem meg. A független review (`ref/spec-review.md`) ezt megtalálta. A javítás után az `input.md` tartalmaz Boot sequence szakaszt, a `meta.yaml` `kb_focus` mezője hat, `file_path` alapján ellenőrzött id-t tartalmaz, és a megjegyzése a valót mondja. Az idézetek ebben a rekordban **szó szerintiek**: a rekord előállításakor minden idézetet gépileg összevetettem az `input.md` szövegével.

## Gépi ellenőrzés

- `tools/validate-meta.sh forms-oracle-provider-integration-01a`: **OK**.
- `tools/validate-spec.sh forms-oracle-provider-integration-01a`: **GO** (exit 0), **figyelmeztetés nélkül** (a K11 WARN megszűnt, mert a `kb_focus` kitöltött).

## Evidence-alapú ellenőrzés (`/job-validate` K1–K11)

| Kritérium | Státusz | Idézet a specből |
|---|---|---|
| K1 — Forrás | PASS | „Klónozd a workspace-be (csak olvasásra, **soha ne pushold őket**)” (27. sor) ; „**Olvasd ki a Forms `corpus/pins.yaml` fájljából**” (29. sor) ; „olvasd a `${CIC_RELAY_PATH}` alatti forrást” (33. sor) |
| K2 — Státusz def + módszer *(kézi)* | PASS | „**implemented** — production kódban hívódik **és** tesztek fedik.” (45. sor) ; „**scaffold** — kódban van, de szándékosan bekötetlen, vagy feltételes elágazás mögött él (`if X == nil`, `if !Flag`” (46. sor) |
| K3 — Tiltott rövidítések | PASS | „❌ „a fájl létezik" ≠ implemented” (53. sor) |
| K4 — Output formátum | PASS | „`output/baseline.md` — a repók és a rögzített commitok” (103. sor) |
| K5 — Ellenőrizhetőség *(kézi)* | PASS | „Minden `implemented` szimbólum mellett production hívó **fájl:sor** vagy a `deadcode` kimenet — nem az agent állítása.” (111. sor) |
| K6 — Negatív példák *(kézi)* | PASS | „❌ Ne csinálj mockot vagy kézi adaptert egy hiányzó leképezés elfedésére” (58. sor) |
| K7 — Call-chain grep + _test.go kizárás | PASS | „`grep -rn "<Szimbólum>" --include="*.go" \| grep -v "_test.go"`” (45. sor) |
| K8 — Claim-evidence tábla | PASS | „`\| Állítás \| Státusz \| Bizonyíték \| Verifikációs módszer \| Kockázat \|`” (106. sor) |
| K9 — Reachability artifact | PASS | „A `deadcode ./...` kimenete (a `module/` és a `tools/oci-extract` alatt) kerüljön az outputba.” (64. sor) |
| K10 — agent.model kitöltve | PASS | meta.yaml `agent.model`: `claude-opus-5` |
| K11 — kb_focus kitöltve | PASS | meta.yaml `kb_focus`: `c7529`, `c7616`, `c7487`, `c7668`, `c7675`, `c7550`; mindegyik `file_path` alapján ellenőrzött (a hat chunkot `get_chunk`-kal olvastam, a `ref/spec-review-2.md` rögzíti), az `input.md` előírja az újraellenőrzést és kimondja a KB határait |

## A review-kör javításai (F1–F5), idézettel

| Javítás | Státusz | Idézet a specből |
|---|---|---|
| F1 — KB boot sequence, KB-korlátok | JAVÍTVA | „## Boot sequence — a KB használata és a határai” (17. sor) ; „**A megadott KB-azonosítókat fájlútvonal alapján ellenőrizd, mielőtt használod**” (21. sor) ; „**a KB a Go fájlokat `.yaml` kiterjesztéssel indexeli**” (21. sor) ; „a KB **2026-10-16-i** állapotot tartalmaz” (22. sor) ; „a **`cic-primitive-forms` nincs a KB-ban**” (22. sor) ; „**a KB nem bizonyíték a jelenlegi implementációra**” (22. sor) |
| F2 — pinek (a `corpus/pins.yaml` szerint), registry explicit | JAVÍTVA | „**A pinek (kötelező, az integráció bizonyíthatóságának alapfeltétele).**” (29. sor) ; „`73ae4692f0680a316d367179ce057195a0031688`” (29. sor) ; „`6db77d4dca4ce3af3be66b3a7a85404fd0b63684`” (29. sor) ; „A `baseline.md` elején legyen **Pin-tábla**” (31. sor) ; „`git clone git@github.com:CentralInfraCore/cic-schema-registry.git`” (27. sor) ; „a `go.mod`, `go.sum`, `Cargo.toml` fájlokat egyik repóban sem módosítod” (69. sor) |
| F3 — nem szennyező mérések, tiszta `git status` | JAVÍTVA | „**Reprodukálható, nem szennyező mérések.**” (93. sor) ; „`git -C <klón> archive <commit> \| tar -x -C <tmp>`” (93. sor) ; „**Tilos** a `git reset --hard`, `git clean`, `git checkout -- .`” (93. sor) |
| F4 — környezet, `NOT MEASURED`, prioritás | JAVÍTVA | „**A mérési környezet rögzítése**” (95. sor) ; „**Az el nem végzett vagy el nem végezhető mérés eredménye `NOT MEASURED`” (97. sor) ; „**Prioritás és keret**” (99. sor) ; „- Q0 és Q1: a modul tényleges CI-jéből” (84. sor) |
| F5 — szó szerinti idézetek | JAVÍTVA | ez a rekord: minden idézet gépileg egyeztetve az `input.md`-vel (a K3 idézet az `input.md` tényleges idézőjeleivel) |

## Összesítés: GO a gépi és az evidence-alapú kapukon (a job indítása külön döntés)

A job **nem lett elindítva**; a külön GO az 01a futtatásához hátravan. A Relay, az Oracle-modul és a Forms production kódja változatlan.
