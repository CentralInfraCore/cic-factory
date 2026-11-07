# Független orchestrátori review a spec ellen: forms-oracle-provider-integration-01a

Dátum: 2026-11-07. A specet **nem módosítottam és nem generáltam újra**, a jobot **nem indítottam**. Vizsgált fájlok: `input.md` (117 sor), `meta.yaml`, `ref/spec-validation.md`, és a modul `devel` ágán elfogadott `docs/design/forms-integration-direction.md` (merge: `3e38886`).

## Eredmény: CONDITIONAL GO

A spec tartalmilag megfelel az irányszerződésnek. **Három szükséges specifikációs javítás** (F1–F3) kell a futtatás előtt; két további pontosítás ajánlott (F4, F5). Egyik sem új funkció, mind a már vállalt követelmények szigorítása vagy egy tényszerű hiba kijavítása.

## A hét kiemelt pont

| # | Pont | Eredmény | Hely és indoklás |
|---|---|---|---|
| 1 | Csak baseline, leltár, leképezés, Q0–Q9, kódmódosítás nélkül | **PASS** | `input.md:9` „Egyetlen repóban sem módosítasz kódot, sémát, CI-t vagy dokumentációt"; a Biztonsági szakasz (97. sor) és a Git szakasz (101. sor) ugyanezt kéri; az 01b/01c kizárása a Kontextusban |
| 2 | A két sémaszerep pontos, új objektummodell nélkül | **PASS** | `input.md:61–62` (C szakasz: intent séma / provider-szerződés / leképezés), `:43` „A `module/schemas/core/vcn.json` **nem primitives-séma**", `:27` „Ne találj ki új primitive-mezőt, enumot vagy grammar-verziót", `:68` „ne vezess be új intent/state ágat" |
| 3 | A commit-pin, függőségek, licencek, TinyGo-próba határai | **PARTIAL** | Van: commit-pin és `2f02a75` minimum (`:19`), licenc és függőségkezelés és a TinyGo-próba a repókon kívüli scratch könyvtárban (`:57`), licenc-döntés tilalma (`:76`). **Hiba:** a `cic-primitives` klónja `devel` ágra van írva (`:19`), a Forms viszont a `corpus/pins.yaml`-ban **rögzített commitot** (primitives `73ae469…`) használja; a `cic-schema-registry` klónozása nincs megparancsolva (csak a pin említése, `:27`). Lásd F2. A klónok szennyeződése (F3) is ide tartozik |
| 4 | A Forms `state_surface`-validáció és a production admission nincs késznek állítva | **PASS** | `input.md:44` (a Forms nem validálja a `state_surface`-t, a hiányzó visszaolvasás nem `null`), `:47` („a P5 admission-szerződés dokumentált terv, nem production kapu") |
| 5 | A reachability-bizonyítás kötelező | **PASS** | `:33` (grep `_test.go` kizárással, fájl:sor, VAGY `deadcode ./...`), az A.1 pont (a `deadcode` kimenet az outputba kerül), `:88` (az orchestrátor ezt közvetlenül ellenőrzi) |
| 6 | Claim–evidence és verifikációs követelmények | **PASS** | `:83` (a tábla pontos fejléce), az „Ellenőrizhető elvárások" szakasz `:86–93` (mintavétel és újrafuttatás, újramérés, kódból idézett aláírások, relay-forrásbizonyíték) |
| 7 | K1–K11, és a K11 figyelmeztetés indoklása | **GO a gépi kapun; a K11 indoklása HELYTELEN** | `validate-meta.sh`: OK; `validate-spec.sh`: GO (exit 0, egyetlen K11 WARN). **De** lásd F1: az indoklás hamis állítást tartalmaz |

## Szükséges javítások (a futtatás előtt)

**F1: a K11 indoklása hamis, és az input.md-ből hiányzik a KB boot sequence.** A `ref/spec-validation.md:8` és a `meta.yaml` megjegyzése azt írja, hogy „az input.md az agentnek írja elő, hogy maga keressen, és minden kiindulási pontnál rögzítse a forrását". **Az `input.md` ezt nem írja elő**: a `grep -n -i "cic-graph\|search_nodes\|search_query\|kb_status\|get_chunk\|boot" input.md` két találata a „KB leírja ≠ implemented" tiltás (41. sor) és a verzió-leltár (57. sor); KB-keresési utasítás nincs. A `/job-create` szabály kötelező elemként írja elő a „Boot sequence" szakaszt a konkrét `search_query` és `search_nodes` hívásokkal, és az `/job-validate` K11 azt kéri, hogy az indoklás igaz legyen.
Javaslat: (a) **Boot sequence szakasz** az input.md-be: `kb_status` (a build-commit és a forrásállapot rögzítése), `search_nodes`/`search_query` a modul ABI-jára, a szerződésekre és a state-modellre, és minden használt chunknál a `get_chunk` `file_path` rögzítése. (b) **Kimondni a KB határait**, amelyeket ez a review a KB-n mért: a KB 2026-10-16-án épült; a modul `5d0a327`-nél (az `#33` és `#34` **előtt**), a Relay `55a899f`-nél van benne; `cic-primitive-forms` **nincs a KB-ban** (`search_nodes("cic-primitive-forms")` üres), a `cic-schema-registry` sincs a források között. A KB tehát csak tervezési kontextus a modulra, **nem bizonyíték a jelenlegi állapotról**; a kód olvasása a klónokból az elsődleges. (c) **`kb_focus`** ezekkel a tartalmilag ellenőrzött idákkal (a visszakapott `file_path` szerint): `c7529` (`docs/design/architecture.md`), `c7616` (`docs/design/specs/state-model.md`, az állapotág példája), `c7487` (`docs/contracts/en/wasm-abi.md`), `c7668` (`module/contracts.yaml`), `c7675` (`module/correspondence.yaml`), `c7550` (`docs/design/primitives-alignment.md`, a `get_chunk` szerint a Relay-hivatkozásról szóló szakasz). Az ida-k a `5d0a327`-es állapotot jelölik és nem stabilak; a spec írja le, minek kell lennie bennük. (d) A `ref/spec-validation.md:8` és a `meta.yaml` megjegyzése javítandó a valóra („a KB-t nem használtuk a spec készítésekor, az id-kat ez a review igazolta").

**F2: a pinek.** A Forms a `corpus/pins.yaml`-ban pinelt commitokra épül (a `cic-primitives` `73ae469…` commitja, és a registry `registry-network-space` pinje). A C szakasz (séma-elérhetőség: fordítható-e a NetworkSpace) **csak a pinelt commitokon** állítható. Javaslat: a `cic-primitives` és a `cic-schema-registry` klónját **a Forms pinjén** állítsa be az agent (`git checkout <pin>`), jegyezze fel a `devel`/`main` HEAD-et külön mint „előrehaladás a pin óta", és írja be a registry explicit klónozását (`git@github.com:CentralInfraCore/cic-schema-registry.git`).

**F3: a mérések nem szennyezhetik a klónokat.** A `go test -coverprofile` fájlt ír, a modul `GOFLAGS=-mod=mod` módja módosíthatja a `go.mod`/`go.sum`-ot; a spec csak annyit mond, hogy „ha véletlenül módosítod, vesd el" (`:101`). Javaslat: a mérések **eldobható másolaton** vagy `-coverprofile=<a repón kívüli út>` kapcsolóval fussanak, és az `agent-output.md`-ben a **végén minden klónra** szerepeljen a `git status --porcelain` üres kimenete.

## Ajánlott pontosítások

**F4.** A Q0/Q1 mérésének módja nincs megadva (az F szakasz Q2–Q9-et nevesíti, `:70–`): egy sor a CI-konfigurációból és egy lokális futásból. A mérések **környezetét** is rögzítse (go verzió, OS, eszközverziók, a hálózat elérhetősége: a `module` mérése a `wazero` letöltését igényli), és **mondja ki, ha egy mérés a hálózat hiánya miatt nem futott**.
**F5.** A `ref/spec-validation.md` két idézete nem szó szerinti (a tipográfiai idézőjel és egy kisbetű/nagybetű eltérés a `„a fájl létezik" ≠ implemented` és a `deadcode` mondatnál). Az `/job-validate` szabálya szerint az idézetnek pontosnak kell lennie.

## Megfigyelés (nem blokkoló)

`meta.yaml` `agent.max_turns: "150"`: az implementációs jobok korábban 150–250 körbe estek; egy négy repós audit mérésekkel nem mért. A `--resume` megoldás létezik. Javaslat: a spec adja meg a prioritást (A, B, C, D kötelező; az F szakasz mutációs próbája utolsó), hogy egy kimerült keret ne a központi leltárt vágja el.

## Következő lépés

A javítások után új `validate-spec.sh` és `validate-meta.sh` futás és egy újabb, rövid review. Az 01a futtatásához **külön GO** kell. Az 01b nem indul. Minden más HOLD változatlan.
