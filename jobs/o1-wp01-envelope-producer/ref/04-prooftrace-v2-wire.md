# ProofTrace V2: wire formátum és a négy eredménydimenzió (javaslat)

**Státusz:** célzott O-1 előkészítési tervezet, **review-ra**; a wire formátumok **NEM elfogadottak** (a D-1–D-13 irányok GO-ja a wire formátumokra nem terjed ki). Nincs implementáció, commit, push, merge, aláírás, countersign, release vagy Factory job. Új Relay-felmérés nem készült: a korábbi mérések és az elfogadott döntések a bemenetek; csak az új szerződésekhez szükséges célzott olvasás történt.
Mérés: 2026-11-27; CIC_Relay `main` `86ea1ab`, cic-module-oracle-cloud `devel` `ae3c962`. `MÉRT` = fájl-olvasás; `UNVERIFIED` = nem mértem; a "nincs hívó/olvasó" állítások grep-alapúak.

## 1. Elv

A **hibrid** modell (D-5): a közvetlenül szükséges identitások a **hash-tartományban**, a részletes evidence **tartalomcímzett hivatkozással**. A hivatkozás csak akkor teljes bizonyíték, ha a tartalom hozzáférhető és ellenőrizhető; egyébként `UNRESOLVED_REFERENCE`. A V1 artifactok változatlanok és V1 szerint ellenőrizhetők; nincs konverzió.

## 2. Mért kiindulás (V1)

| Tény | Hely |
|---|---|
| `ProofTraceStep`: `Name` (= nyers lépés-szöveg), `Module` (= `név@verzió`), `InputHash`, `OutputHash` | `core/cabinet/proof_trace.go:12–17`, `service.go:319–324` |
| A lánc-hash `CICCHAINv1` prefixű, a mezők összefűzött sha256-ja | `proof_trace.go:105–133` |
| A **perzisztencia** már külön objektum: `ProofStatus{Persisted, Commit, ErrorCode}` a `SetResponse` mellett, **nem** a hash-tartományban; a kommentje kimondja: a végrehajtás sikere, a lánc-hash és a perzisztencia három külön tény | `core/cabinet/api_set.go:18–32` |
| Egy lépés-hiba a futás hibájával tér vissza, **trace nélkül** | `service.go` (a lépés-ciklus hibaágai) |
| A `ProofTraceStepFromActuation` egy host-hívás non-secret digestjeit lépéssé vetíti | `proof_trace.go` |
| A `VerifyProofArtifact` a szerkezetet és a láncot ellenőrzi, aláírást nem; ugyanazt a `ComputeChainHashV1`-et használja, mint az előállító | `cmd/relay/proof_verify.go:40–120` |

## 3. A V2 artifact (`schemas/prooftrace-v2.schema.json`; `examples/valid/prooftrace-v2-ok.json`)

**Hash-tartomány (az artifact):** `kind: ProofArtifact`, `version: "2.0"`, `chain_version: "CICCHAINv2"`, `workflow{id, source_digest}`, `steps[]`, `outcome{execution, authorization}`, `chain_hash`. A **`chain_hash`** a `chain_hash` nélküli artifact **kanonikus bájtjainak** `CICCHAINv2\0`-tartomány-prefixű sha256-ja (a kanonizálás nyitott).

**Lépés:**

| Mező | Kötés | Megjegyzés |
|---|---|---|
| `index`, `name` | közvetlen | a nyers lépés-szöveg is megmarad |
| `requested.module_id`, `requested.operation`, `requested.presented_artifact_digest?` | közvetlen | **V2-01: a KÉRT identitás**: mit kértek végrehajtani; **minden** lépésnél létezik, a betöltés vagy dispatch előtt elutasítottnál is |
| `executed.artifact_digest` | közvetlen | csak ha a végrehajtási fázist elérte: a **nyers WASM sha256-ja** (D-10) |
| `executed.executed_digest` | közvetlen | a ténylegesen példányosított (kanonikus) bájtok sha256-ja (lásd 01) |
| `executed.manifest_digest`, `executed.envelope_digest` | közvetlen | a teljes release-manifest nyers bájtjainak digestje (ENV-01) és a hitelesített envelope-identitás (ENV-03; `null` csak `transitional`/`dev` állapotban) |
| `executed.dispatched`, `executed.profile{id, digest}` | közvetlen | a ténylegesen dispatch-elt string; a profil **tartalmi digestje**, nem csak a neve |
| `executed.trust_state` | közvetlen | `authenticated` / `transitional` / `dev`; `authenticated` esetén az `envelope_digest` kötelező (a séma kikényszeríti) |
| `outcome.execution` | közvetlen | `SUCCEEDED` / `REJECTED` / `FAILED` / `ABORTED` |
| `outcome.authorization` | közvetlen | `ALLOWED` / `DENIED` / `NOT_EVALUATED` |
| `input_digest`, `output_digest` | közvetlen | `output_digest: null` megengedett (elutasított/hibás lépés) |
| `references.execution_context.digest` | **hivatkozás** | policy-digest, realization context (O-4), principal (R6) |
| `references.authorization_decision.digest` | **hivatkozás** | a döntési mechanizmus rekordja; **kötelező**, ha `authorization` `ALLOWED` vagy `DENIED` (a séma kikényszeríti: mért) |
| `references.host_interactions.{digest,count}` | **hivatkozás** | a rendezett lista digestje; a megtagadott és sikertelen hívásokat is tartalmazza |

**Szabály (V2-01):** a `REJECTED` lépésnek **nincs `executed` blokkja** (nem állíthat nem létező végrehajtási identitást), van `rejection{phase: admission|dispatch|policy, code}` rekordja, nincs kimenete és nincs host-interakciója; `SUCCEEDED`/`FAILED`/`ABORTED` lépésnek `executed` blokkja **kötelező**, `rejection`-je tilos (a séma kikényszeríti: mért; a hibásan épített negatív példa is a harnessen akadt fenn).

## 4. A négy független eredménydimenzió

| Dimenzió | Ki állítja | Hol él | Értékek |
|---|---|---|---|
| **Execution outcome** | a Relay | az artifact (`outcome.execution`, lépésenként is) | `SUCCEEDED`/`REJECTED`/`FAILED`/`ABORTED` |
| **Authorization (policy) outcome** | a Relay | az artifact (`outcome.authorization`) | `ALLOWED`/`DENIED`/`NOT_EVALUATED` |
| **Evidence outcome** | a Relay (a recorder jelentése) | az artifact **burka** (`persistence`: a **hash-tartományon kívül**, a meglévő `ProofStatus` mintájára) | `persisted: true` + `commit` / `false` + `error_code` |
| **Verification outcome** | a **verifier**, nem a Relay | külön objektum (`schemas/verification-result.schema.json`) | `COMPLETE`/`INCOMPLETE`/`FAILED` |

**A perzisztencia-objektum (`schemas/prooftrace-v2-persistence.schema.json`) kötött és hiteles:** kötelezően hordozza az `artifact_chain_hash`-t (az artifact digestje, amelyre vonatkozik: kötés nélküli státusz érvénytelen), a `recorder` azonosítóját; `persisted: true` esetén `commit` **és `attestation`** (`git-signed-commit` vagy `recorder-signature`, `signer_key_id` + `signature_digest`) **kötelező**: aláírás/attesztáció nélküli "tárolva" állítás nem külső bizonyíték; `persisted: false` esetén `error_code`, commit és attesztáció tilos. Az attesztációt a verifier ellenőrzi (a recorder kulcsának befogadása az admission A1 szerint), a Relay nem hitelesíti saját magát.

**Miért nem az artifactban a perzisztencia:** egy artifact nem állíthatja saját magáról, hogy tartósan rögzült (körkörös, és a hash-tartományt a rögzítés eredménye módosítaná). A séma ezt kikényszeríti: a `persistence` az artifactban **tiltott** (mért). A **`VerificationResult`** a független verifier állítása: kötelezően hordozza a `verifier{id, version, implementation_digest}`-et és a `subject{artifact_chain_hash, persistence_digest?}`-et (melyik artifactra és melyik perzisztencia-rekordra vonatkozik); verifier-azonosító nélküli eredmény érvénytelen (mért). A Relay a saját artifactjáról ilyen eredményt **nem állíthat ki** (felelősségi határ: Relay: artifact; döntési mechanizmus: authorization evidence; recorder: persistence; független verifier: VerificationResult). A verifier a négy dimenziót **külön adja vissza**; a `VERIFIED` csak `verification: COMPLETE` és üres `unresolved_references` mellett lehet (mért).

**A #186 példa (logikai, nem elfogadott enum-szerződés; a V2-02 szerint két külön állítás):** `execution: SUCCEEDED`, `authorization: ALLOWED`, `evidence: NOT_PERSISTED`, `verification: COMPLETE` → **`evidence_verdict: VERIFIED`** (a rendelkezésre álló bizonyíték hiteles és teljes), **`acceptance: NOT_ACCEPTED`** (a kötelező perzisztencia-feltétel nem teljesült); példa: `examples/valid/verification-evidence-not-persisted.json`. A korábbi `verdict` mező megszűnt.

## 5. Új képesség, nem csak új mező (önálló implementációs feladat: **trace-on-failure**)

A V1 trace csak a **sikeresen befejezett** futásokról készül. A V2-höz kell: **trace-on-failure**: a `REJECTED` (dispatch-elutasítás), `FAILED`, `ABORTED` futás is artifactot ad, host-interakció nélkül vagy a megtagadott hívásokkal. Ez a Cabinet lépés-ciklusának módosítása (D-5 új képesség); **nem** része ennek a csomagnak, a szerződés a követelményt rögzíti.

## 6. V1 és V2

Külön hash-tartomány (`CICCHAINv1` / `CICCHAINv2`), külön séma-verzió; a verifier a deklarált verzió szerint ellenőriz (nem találgat); V1 artifact nem elégíthet ki V2-osztályú állítást (op identity, modul-artifact, manifest, trust állapot, host-interakció); a V1 változatlan (a `prooftrace-v1-is-not-v2` példa mért elutasítása).

## 7. Acceptance (production-szint)

| # | Kritérium |
|---|---|
| AC-V2-01 | a módosított profil eltérő `profile_digest`-et ad |
| AC-V2-02 | az elutasított dispatch `REJECTED` artifactot ad, kimenet és host-interakció nélkül |
| AC-V2-03 | a megtagadott host-hívás a `host_interactions` listában `denied`-ként szerepel |
| AC-V2-04 | hiányzó evidence-hivatkozás: `UNRESOLVED_REFERENCE`, nem `PASS` |
| AC-V2-05 | az evidence-perzisztencia hibája **nem** állítja, hogy a művelet nem történt meg (`execution` változatlan) |
| AC-V2-06 | `authenticated` csak `envelope_digest`-tel (hitelesített envelope-identitás) |
| AC-V2-07 | a V2 rekord V1 tartományban és fordítva elutasított |
| AC-V2-08 | a verifier a négy dimenziót külön adja vissza |
| AC-V2-09 | a perzisztencia-státusz `artifact_chain_hash` nélkül, vagy `persisted: true` attesztáció nélkül elutasított |
| AC-V2-10 | a `VerificationResult` verifier-identitás és subject nélkül elutasított; a Relay-generált eredmény nem elfogadott verifier-állítás |
| AC-V2-11 | `ALLOWED`/`DENIED` lépés `authorization_decision` hivatkozás nélkül elutasított |
| AC-V2-12 | a perzisztencia-attesztáció kriptográfiailag ellenőrzött és az `artifact_chain_hash`-hez kötött (a séma-validáció nem bizonyíték) |
| AC-V2-13 | a `VerificationResult.implementation_digest` deklarációja nem elfogadott bizonyíték: a verifier-azonosság külön igazolt |

## 7b. Mit nem bizonyít a séma (production-verifier acceptance)

A JSON Schema csak a **meglétet és szerkezetet** ellenőrzi. A verifiernek **ténylegesen** kell bizonyítania: (a) a perzisztencia-attesztáció kriptográfiai hitelességét és azt, hogy az `artifact_chain_hash`-re vonatkozik (AC-V2-12); (b) hogy a recorder kulcsa befogadott (admission A1); (c) a `VerificationResult.implementation_digest` **deklarációja nem bizonyíték** arra, hogy az az implementáció végezte az ellenőrzést: a verifier-azonosságot külön (pl. aláírt/attesztált verifier-kiadás, vagy a vektorokon való független reprodukálás) kell igazolni (AC-V2-13). Ezek konkrét acceptance követelmények, nem új architekturális kérdések.

## 8. Nyitott

~~A kanonikus forma és a tartomány-prefix~~ (lezárva: 9. szakasz V2-03; a független implementáció-azonosság a vektorokra vár); az evidence tárolása és exportja (O-5); a `host_interactions` és `execution_context` rekord wire formátuma; a trace-on-failure Cabinet-oldali megvalósítása; a `proof_artifact` séma-verzió (`2.0`) elnevezése.

## 9. Review-korrekciók V2-01–03 (2026-11-27; normatív)

**V2-01 (kért és végrehajtott identitás).** A lépés `requested` blokkja (mit kértek) mindig létezik; az `executed` blokk (mi hajtódott végre) **csak** a végrehajtási fázis elérésekor. A `rejection.phase` (`admission`, `dispatch`, `policy`) mondja meg, hol állt meg a művelet. Referencia-példa: `prooftrace-v2-rejected-before-load`. A trace-on-failure Cabinet-oldali megvalósítása önálló implementációs feladat.

**V2-02 (`VERIFIED` pontos jelentése).** A `VerificationResult` két külön állítást tesz (`schemas/verification-result.schema.json`):

| Állítás | Jelentés | Szabály |
|---|---|---|
| `evidence_verdict`: `VERIFIED`/`NOT_VERIFIED` | a bizonyíték **hitelesen és teljesen** reprezentálja a történteket (függetlenül attól, hogy mi történt) | `VERIFIED` ⇒ `verification: COMPLETE` és nincs `unresolved_references` |
| `acceptance`: `ACCEPTED`/`NOT_ACCEPTED`/`NOT_EVALUATED` | a művelet a kötelező policy- és evidence-feltételeket teljesítette | `ACCEPTED` ⇒ `evidence_verdict: VERIFIED` ∧ `execution: SUCCEEDED` ∧ `authorization: ALLOWED` ∧ `evidence ∈ {PERSISTED, NOT_REQUIRED}` ∧ `acceptance_policy_digest` megadva |

Egy megtagadott művelet bizonyítéka lehet `VERIFIED` és a művelet mégis `NOT_ACCEPTED` (példa: `verification-denied-operation-with-verified-evidence`). Az `acceptance_policy_digest` rögzíti, melyik policy szerint értékelt a verifier. Mindkét állítás a **független verifier**é; a Relay egyiket sem állíthatja a saját artifactjáról.

**V2-03 (kanonikus hash-szerződés, `CICCHAINv2`).** A hash-input rögzített sorrendű, LF-lezárt `kulcs=érték` sorok (nincs JSON-újraszerializálás): `CICCHAINv2` tartomány-sor; `version`, `workflow.id`, `workflow.source_digest`, `outcome.execution`, `outcome.authorization`, `steps=<n>`; lépésenként `step.<i>.name_sha256` (a szabad szöveg csak a UTF-8 bájtjainak sha256-jaként lép be), a `requested.*`, `outcome.*`, `input_digest`, `output_digest`, `references.*` mezők, majd `rejection=present|absent` (+ `phase`, `code`) és `executed=present|absent` (+ a nyolc `executed.*` mező). `null` = a `null` literál; sortörést tartalmazó vagy nem ASCII érték **elutasított**; a `chain_hash` mező nem része a bemenetnek. `chain_hash = sha256(hash-input)`. **Referencia:** `chain_bytes` / `chain_hash` a `build_o1_schemas.py`-ban; a példák `chain_hash` mezője a számított érték (11 ellenőrzés: kulcssorrend-függetlenség, minden azonosság-mező érzékenysége, az `executed` csoport eltávolítása, sortörés-elutasítás). Ez **referencia-szintű, egy implementációra épülő** szerződés: két független implementáció azonosságát a közös vektorok (wire-elfogadás után) bizonyítják.

**A perzisztencia és a verifier-azonosság** (7b) acceptance-követelménye változatlan: a séma szerkezetet ellenőriz, a kriptográfiai hitelességet a verifier.
