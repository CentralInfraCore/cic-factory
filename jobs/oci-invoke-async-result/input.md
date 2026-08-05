# oci-invoke-async-result — az `Invoke()` ne jelentsen hamis befejezettséget

## Ki vagy — olvasd el először

**Te vagy a végrehajtó agent.** Te írod a kódot ebben a jobban. Nem te indítottad
ezt a jobot, és nincs mire várnod: a munka a te dolgod, most.

Ahol a szöveg „az orchestrátor"-t említi, az egy **másik** szereplő (a `workdir`
operátora, aki a specet írta és a valós OCI verifikációt futtatja majd). Ne
beszélj az ő nevében, és ne írj állapotjelentést a jobról — írd meg a kódot.

## Reasoning mód

**implementation.** A hiba **azonosítva és valós OCI-n mérve** van — nem kell
újra felfedezned, és nem kell eldöntened, hogy hiba-e. A dolgod: megjavítani úgy,
hogy a javítás igazolható legyen.

## A hiba — mérve, nem feltételezve

2026-08-05-én az orchestrátor lefuttatta a `TestManualRealOCIInvoke`-ot valós OCI
ellen (`ChangeInstanceCompartment` egy élő instance-en). Mérés:

| Mit | Mérés |
|---|---|
| A modul `Invoke()` eredménye | `{"status":"ok","result":{"status":"succeeded","operation":"ChangeInstanceCompartment","http_status":202, ...}}` |
| Amit OCI ténylegesen válaszolt | `202 Accepted` **+ `opc-work-request-id: ocid1.coreservicesworkrequest.oc1.eu-frankfurt-1...`** (közvetlenül mérve `oci raw-request`-tel ugyanarra a végpontra) |

Vagyis: **az `Invoke()` `succeeded`-et jelent egy aszinkron műveletre, és eldobja
a Work Request id-t.** A hívónak nincs mit pollozni, és azt hiszi, kész van.

A kód, ahol ez történik (`module/provider.go`, a `devel` ág állapota):

- `:626` — `operationResult` struct: **nincs `work_request_id` mezője**
- `:668` — a státusz fixen `"succeeded"`, csak `>= 400` esetén lesz `"failed"`;
  a `headers`-ből csak `etag` és `opc-request-id` kerül át

Az `Execute`/`Destroy` a saját útján ezt **helyesen** csinálja, és a kód ki is
mondja az elvet (`:983-985`):

> „An async op (202 Accepted, or an opc-work-request-id) is not done — the caller
> must poll the Work Request. **Surface the id, not a false success.**"

`executionStep` (`:878`) ezért tartalmaz `WorkRequestID`-t, és a
`Destroy()` ugyanaznapi valós futása a helyes alakot mutatja:
`status: "accepted"` + `work_request_id`, amit a `Poll()` végig is vitt
`SUCCEEDED`/`terminal: true`-ig.

**Az `Invoke` az egyetlen kódút, ami ezt az elvet nem követi.**

### Miért számít ez a ProofTrace-nek

A `kb_focus`-ban megadott chunkok (olvasd el őket **először**) mutatják, hogy a
ProofTrace lépésenként rögzíti a végrehajtás ujjlenyomatát. Egy „succeeded",
ami valójában „elindult, de még fut", **hamis bizonyíték** — pont az, aminek a
kizárása a rendszer célja. A Work Request id elvesztésével pedig nincs mihez
kötni a későbbi terminális állapotot.

## A feladat

### A) Az `Invoke()` async-eredménye — ez a job lényege

1. `operationResult` kapjon `work_request_id` mezőt (`json:"work_request_id,omitempty"`),
   ugyanazzal a szemantikával, mint `executionStep.WorkRequestID`.
2. Az `Invoke()` olvassa ki a válasz `opc-work-request-id` headerét.
3. A státusz `"accepted"` legyen `"succeeded"` helyett, ha a művelet aszinkron —
   **ugyanaz a szabály, amit a másik kódút már használ**, ne találj ki újat.
   Olvasd el, hogyan dönti el ezt a meglévő kód (`:948-964` és `:983-985`), és
   kövesd. Ha a két hely szabálya nem pontosan azonos, a **meglévő,
   valós OCI-n igazolt** viselkedés a minta, és írd le az eltérést az outputban.
4. A `>= 400` ág maradjon változatlan (`failed` + `ociError`).

### B) Másodlagos, külön commitba — a `404` elveszti az OCI kódját

Ugyanaznap mérve: a `Destroy()` egy 404-et szándékosan rövidre zár
(`:598`, dokumentálva `:582-584`-ben) és envelope-szintű hibát ad
`"resource already gone: <ocid>"` üzenettel. Ez a viselkedés **maradjon**, de
így az OCI natív `code`/`message`-e **elveszik**, míg minden más hibaúton
megmarad (mérve: `409` → `provider_code: "IncorrectState"` + OCI üzenete szó
szerint; `400` → `provider_code: "InvalidParameter"`).

A kérés: a 404 ág is **őrizze meg** az OCI `code`/`message`-ét (a
`providerError`-nak már van `ProviderCode` mezője, és az `ociError` már
kitölti), a `Class: not-found` és az envelope-szintű alak megtartásával.

**Ha A és B közül bármelyik nagyobbnak bizonyul, mint amit itt leírtam: A az
elsődleges.** B kihagyható, ha indokolod — de akkor mondd ki az outputban, hogy
kimaradt, ne hallgasd el.

## Kemény korlátok

1. **Ne hozz létre valós OCI erőforrást, és ne hívj valós OCI-t.** A javítás
   fixture-szinten igazolandó; a valós futtatás az orchestrátoré (lásd
   „Verifikáció"). Ok: egy turn-limitbe futó implementációs job futó VM-et
   hagyna a tenancyben — ez már négyszer megtörtént.
2. **A CIC-Relay READ-ONLY.** Relay-igény → `R#` tétel a
   `docs/design/relay-requirements.md`-be, a relay **forrásából** vett
   bizonyítékkal. Ne javítsd a relayt, és ne duplikáld a logikáját ide.
3. **Ne köss be primitives/YANG sémát.**
4. **`git add -A` TILOS** — a `make build` untracked, nem-gitignore-olt `.yaml`
   sidecarokat hagy (mérve: `module/contracts.yaml`, `module/manual_real_oci_test.yaml`),
   és a `MANIFEST.sha256` `git ls-files`-ra épül, tehát a szemét az **aláírt
   manifestbe** kerülne. Explicit path-listával commitolj, és `git status --short`-tal
   nézd meg, mi menne be.
5. **A repo dokumentációja angol.** Ez az `input.md` magyar, de minden, ami a
   modul-repóba kerül — kód, komment, `docs/**` — **angolul**.
6. **Ne írd át a `manual-verification.md` coverage tábláját „verified"-re** az
   `invoke` sorban. Az a sor a valós futtatás jegyzőkönyve; te fixture-t írsz.
   A javítás tényét írd le, a `verified` státuszt az orchestrátor adja meg,
   miután újra lefuttatta.

## Definition of Done — mind ellenőrizendő, futtatott kimenettel

1. `operationResult` tartalmaz `work_request_id`-t; egy fixture-teszt, ami egy
   mock 202 + `opc-work-request-id` válaszra **`accepted`** státuszt és a
   **kiolvasott id-t** várja el, zölden fut.
2. Regressziós fixture: egy szinkron (200/204, work-request nélküli) invoke
   továbbra is `succeeded`, és nincs `work_request_id` a JSON-ban (az
   `omitempty` miatt).
3. Regressziós fixture: `>= 400` továbbra is `failed` + helyes `error_class`
   és `provider_code`.
4. **A negatív irány is mutatva:** vidd vissza a javítást egy pillanatra (vagy
   írj szándékosan hibás mock-ot), és mutasd meg, hogy az új teszt **bukik**
   nélküle. Egy teszt, ami a hiba jelenlétében is zöld, nem bizonyít semmit.
5. (B esetén) fixture arra, hogy a 404-es destroy envelope-hiba `provider_code`-ja
   és üzenete az OCI-tól jön, nem generált szöveg.
6. `make check`, `make golang.quality`, `make wasm.build` + `wasm.test`,
   `make manifest-verify`, `make docs.link-check` — mind zöld, **futtatva**.
7. CI zöld a pusholt feature branchen, és a `headSha` **egyezik** a tesztelt
   committal (`gh run view <id> --json headSha,conclusion`).

## Tiltott rövidítések — ezek NEM bizonyítékok

- **„a mező létezik a structban" ≠ implemented.** A kérdés az, hogy a
  production kódút *kitölti-e*.
- **„a teszt lefut" ≠ a teszt bizonyít.** Lásd DoD 4: mutasd meg, hogy a régi
  kóddal bukik.
- **„exit code 0" ≠ sikeres.** Olvasd el a kimenetet is, ne csak a státuszt.
- **„a CI zöld" ≠ ez a commit zöld.** Egyeztesd a `headSha`-t.
- **„a fájl létezése" ≠ elérhető kódút.** Lásd a reachability előírást lent.

## Kötelező output

A `jobs/oci-invoke-async-result/output/` alá, a cic-factory klónodban:

### `output/agent-output.md`
Mit csináltál, mit nem, és miért. Ha B kimaradt, itt mondd ki.

### `output/claim-evidence.md`
Claim–evidence tábla, pontosan ezekkel az oszlopokkal:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |

Minden DoD-pont egy sor. Amihez nem tudsz verifikációs módszert írni, az
**„nem igazolt"** — ne hagyd ki, és ne írd „igazolt"-nak.

### `output/reachability.md`
A módosított kódút **production** elérhetősége — `grep -rn` kimenettel, a
`_test.go` fájlok kiszűrésével, vagy `deadcode ./...` outputtal. Konkrétan:
melyik production hívó (`file:line`) éri el az `Invoke()`-ot és az új mezőt
kitöltő ágat. „A szimbólum létezik" nem elég.

## Verifikáció — ez NEM a te dolgod, de készítsd elő

A valós OCI futtatás az orchestrátoré (`ChangeInstanceCompartment` egy élő
instance-en, második compartmenttel). Írd meg neki a pontos receptet:

### `output/orchestrator-verification.md`
Futtatható parancsok, várt kimenettel — mit kell látnia, hogy a javítás igazolt
legyen valós OCI-n. Konkrétan: milyen `status`-t és milyen `work_request_id`-t
vár, és hogyan folytatja a `Poll()`-lal a terminális állapotig.

**Fontos futtatási tudás, amit az orchestrátor mért 2026-08-05-én, és ami a
doc receptjéből hiányzik:** a `docs/design/manual-verification.md` host Go
toolchaint feltételez, de a Go a **builder konténerben** van, és a
`docker-compose.yml` **nem mountolja** a `$HOME/.oci`-t. A `mk/golang.mk:141-143`
azt javasolja, tegyük a kulcsot a repo alá gitignore-olt path-ra — **de a
`.gitignore`-ban nincs `*.pem` szabály**, tehát az a tanács így csapda. Ami
működött:

```bash
docker compose run --rm --no-deps -v "$OCI_KEY_PATH:/run/oci-key.pem:ro" \
  -e OCI_KEY_PATH=/run/oci-key.pem -e OCI_TENANCY_OCID -e OCI_USER_OCID \
  -e OCI_FINGERPRINT -e OCI_REGION ... -e REAL_OCI_TEST=1 \
  builder sh -eu -c 'cd /app/module && go test -tags manual_real_oci -count=1 -run ... -v ./'
```

Ha ezt a receptet a `manual-verification.md`-be is beírod (angolul), az önálló
érték — a következő futtatónak ne kelljen újra kitalálnia. A `.gitignore`
`*.pem` szabályát is felveheted, ha indokolod.

## Git

- A modul repo `devel` ágáról ágazz: `feature/oci-invoke-async-result`.
- Commitolj és pushold a feature branchre. **PR-t ne nyiss**, és `main`-re/`devel`-re
  ne pushold — a merge az orchestrátoré.
- A cic-factory klónodban az `output/` a saját feature branchedre megy.
