# A CIC/Relay PoC Technikai Magja: A Bizalom Bizonyítása

A CIC/Relay PoC technikai magja egy **bizalom-infrastruktúra formalizált alapja**, ahol minden komponens és folyamat a **bizonyíthatóság, önigazolás és auditálhatóság** elveire épül. A rendszer nem külön modulok laza összessége, hanem egy egységesen szervezett architektúra, amelyben a logikai, fizikai és gazdasági rétegek egymást erősítve építik fel a „bizalom bizonyításának” láncolatát.

---

### 1. 🏛️ CIC / OIS Elvi Réteg

A **Central Infrastructure Core (CIC)** szolgál az egész ökoszisztéma gyökereként: ez a **bizalom technológiai manifesztuma**. Az **OpenIntentSign (OIS)** mechanizmus az intenciók, kötelezettségek és következmények összekapcsolt logikai rendszerét adja, ahol minden döntés és művelet önmaga bizonyítéka.

A cél a bizalom **bizonyítható állapottá** tétele: *nem az ember bizonyít, hanem a technológia*. A CIC így **önigazoló architektúraként** viselkedik – egy olyan térként, ahol a rendszer minden komponense aláírások, hash-ek és metaadatok révén önmagát hitelesíti.

### 2. 🛡️ Schema → Gateway → ProofTrace

A rendszer adatfolyamainak kapuja a **schema-validálás**, amely egységes szerkezetet, formát és ellenőrizhető viselkedést biztosít. Minden adat a modulba lépés előtt átmegy ezen a validációs szűrőn, ahol a rendszer – ha szükséges – **injektálja a schema-ban definiált default értékeket** jelölten, az audit-láncban rögzítve.

Az így validált objektumokból jön létre a **ProofTrace**, ami az *actor, intent és schema* szintű bizonyítékot összefogó entitás. Ezzel a rendszer minden eseménye saját, kriptográfiailag hitelesített nyomvonalat hoz létre.

### 3. 🌳 IaC (Infrastructure as Code) + State Ág

Az IaC nem csupán konfigurációs sablon, hanem a **valós állapot tükre** is. A deklarált (desired) és a valós (actual) állapot egyaránt commitálva van a state-ágban, amelyet a ProofTrace validál. A *drift* – vagyis az eltérés – mérhető és dokumentált, így a rendszer automatikusan elszámoltathatóvá válik.

Ez a megközelítés hozza létre a **Declarative Accountability** elvét: a rendszer nemcsak deklarálja, hanem bizonyítja is a saját állapotát.

### 4. 🔗 ProofTrace Réteg

A ProofTrace a teljes architektúra gerince, ahol minden tranzakció, állapotváltozás és döntés **determinisztikusan hash-elt** formában rögzül. Azonos bemenet azonos hash-t eredményez, ezáltal a bizonyítás reprodukálható és auditálható.

A ProofTrace **Merkle-láncként** viselkedik, a metaadatok pedig biztosítják a kontextust. PBS integrációval létrejön a **Proof of State Existence (PoSE)**, amely a logikai (ProofTrace) és a fizikai (PBS snapshot) réteget egységbe fogja.

### 5. 💰 Licenc és Gazdasági Modell

A CIC/Relay ökoszisztéma **CC BY-NC-SA 4.0** licenc alatt működik, amely lehetővé teszi az oktatási, kutatási és nem kereskedelmi felhasználást. A monetizáció a **validált proof állapotokra** épül – azaz a szolgáltatási oldalon keletkező, hitelesített bizalmi érték az elszámolási alap.

A licenc mennyiségi modellben működik (**CICmeta valutában (C)**), felhasznált db/év alapján:
*   **Relay:** C100
*   **Host:** C20
*   **Modul:** C20

A licenc továbbértékesíthető ProofNode cluster fenntartás mellett. A modul release metaadataiban kötelező a `licenseCA`, `unlicensed_behavior` és `support_end` megadása, biztosítva az átlátható ökoszisztéma működést.

### 6. 🛠️ Technológiai Implementációs Mag

A PoC **Golang** alapokon nyugszik, közel **90%-os unit-teszt lefedettséggel**. Az infrastruktúra verzionáltan fejlődik:

*   **v1:** Proxmox + VyOS + OpenSwitch + Bastion + Vault(mem) + Relay – a *lokális, önálló bizonyítási kör*.
*   **v2:** + Talos cluster, Gitea, Nexus, CloudNativePG, Prom/Grafana – a *menedzselt, megfigyelhető és dokumentált környezet*.
*   **v3:** + két telephely, k8s, titkosított kapcsolat – az *elosztott, redundáns bizonyítási architektúra*.

Az IaC generált, verziózott, minden komponens auditálható. A PBS deduplikált, időbélyeges mentésekkel szolgálja a fizikai bizonyítást. A Graylog csak emberi forenzikára opcionális, a Nexus és Prometheus optimalizált cleanup és retention policy-ket használ a gazdaságos működéshez.

### 7. 🔍 Biztonsági és Audit Szint

A biztonsági réteg a **teljes életciklusra kiterjed**: a kódolástól a bizonyításig. A *race, fuzz és mutációs tesztelés* kötelező. A **canonical JSON marshalling** biztosítja a determinisztikus hash-elést. A kulcskezelés **Vault vagy HSM alapon** történik, fájlba mentés tilos.

A *replay-védelem* és *timestamp-window* mechanizmusok garantálják a tranzakciók egyediségét. Minden build **SBOM-mal és reprodukálhatósági metrikákkal** auditált, a **STRIDE modell** alapján dokumentált és mitigált.

---

**Eredmény:** a CIC/Relay PoC technikai magja egy **önigazoló, determinisztikus és auditálható infrastruktúra**, amely a bizalmat bizonyítható állapottá alakítja. Ez a keretrendszer nem csak fejlesztés, hanem egy új szemlélet: a **technológia által bizonyított bizalom** alapja.

---

### 8. 🎬 Élő Demonstráció: Terraform → CIC → Rollback

A következő demonstráció a teljes bizalom-láncolatot mutatja be valós, megfigyelhető körülmények között. Nem szimulációról van szó: **minden commit, hash és aláírás valós, auditálható entitás**, amely a rendszer önigazolásának bizonyítékaként marad meg.

---

#### 8.1 Fázis: Infrastruktúra felhúzása Terraformmal

A Terraform egy deklaratív IaC-leírásból kiindulva kézzel szokásos módon nativan **felprovizionálja az infrastruktúrát** (pl. hálózati szegmens, virtuális gépek, tűzfalszabályok). A folyamat zárása után az infrastuktúrából a CIC **rögzíti az OIS-Intent deklarációt**: ki, mit, milyen policy alapján rendelt el.

A provizionálás befejeztével:
- a CIC **ProofTrace-eseményt** hoz létre (actor, intent, schema, timestamp, signature),
- az IaC git repo `state/` ága **automatikusan commitálódik** a levezetett fizikai állapottal,
- a képernyőn élőben látható a könyvtárstruktúra és a commit tartalma – ez az első **igazolt CommitRef**.

```
state/ ág → commit #1
  ├── infra.tf.json        ← desired state (deklarált)
  ├── actual_state.json    ← valós állapot (PBS snapshot)
  └── prooftrace.json      ← ProofTrace entitás (hash, aláírás)
```

> *A commit nem csupán egy pillanatkép. Az a pillanat, ahol a szándék és a valóság először találkozik.*

---

#### 8.2 Fázis: Kézi módosítások – a drift keletkezése

Az infrastruktúrán **4–5 alkalommal kézi beavatkozás** történik (pl. szabály-módosítás, erőforrás-átnevezés, konfiguráció-felülírás). Minden egyes módosítás után:

1. A CIC **észleli az eltérést** a ProofTrace lánc és a PBS (tényleges állapot) között.
2. A drift típusa meghatározásra kerül: `SOFT_DRIFT` vagy `RECONCILIABLE_DRIFT`.
3. Az IaC git repo `state/` ágán **új commit keletkezik**, amely tartalmazza:
   - az eltérés leírását (`drift: true`),
   - az új tényleges állapotot,
   - a ProofTrace-lánc folytatódó elemét.

A képernyőn **pörögnek a commitok** – minden egyes beavatkozás egy auditálható bizonyítési eseménnyé válik, amelyet visszamenőleg sem lehet eltávolítani vagy módosítani.

```
commit #2  ← kézi módosítás #1  (SOFT_DRIFT → reconciled)
commit #3  ← kézi módosítás #2  (SOFT_DRIFT → reconciled)
commit #4  ← kézi módosítás #3  (RECONCILIABLE_DRIFT)
commit #5  ← kézi módosítás #4  (SOFT_DRIFT → reconciled)
commit #6  ← kézi módosítás #5  (RECONCILIABLE_DRIFT)
```

---

#### 8.3 Fázis: Az infrastruktúra törlése – Hard Drift

Az egész infrastruktúra leállításra és törlésre kerül. A CIC ezt nem csendben engedi el:

- A PBS gyökér-hash **null állapotba kerül** – fizikailag semmi nem létezik.
- A ProofTrace lánc azonban **nem semmisül meg**: a lánc utolsó igazolt CommitRef-je megmarad.
- A rendszer **`HARD_DRIFT`-et** rögzít: a valós fizikai állapot nem vezethető le az utolsó érvényes ProofTrace-ből.
- A `state/` ágon ez is **commitálódik** – az eltűnés is bizonyított tény.

> *A rendszer nem tud „elfelejteni". A törlés is esemény, a semmisség is állapot.*

---

#### 8.4 Fázis: Visszaállítás – az Intent ág és az infra újjáépítése

A `state/` ágon **visszanézünk a commit-történetbe**: kiválasztjuk azt az igazolt CommitRef-et, amelynek állapotát helyre szeretnénk állítani (pl. `commit #3` – az első kézi módosítás előtti stabil állapot).

Ezt a commitot **mergeljük az `intent/` ágra**:

```bash
git checkout intent/main
git merge state/commit-3-ref
git push origin intent/main
```

A push pillanatában:
- a CIC felismeri az `intent/` ágon az új deklarált kívánt állapotot,
- **OIS-ellenőrzés** fut: jogosult-e a rollback-szándék az adott policy alapján,
- ha az Obligation teljesül → a Terraform **élőben felhúzza az infrastruktúrát** a meghatározott korábbi állapotnak megfelelően,
- a képernyőn valós időben látható az erőforrások megjelenése.

Minden lépés rögzül a ProofTrace-ben: **nem csupán az infra jött vissza, hanem bizonyítható, hogy miért és ki által**.

---

#### 8.5 A Git Commit Anatómiája – Bizalom a Láncolatban

A CIC/Relay rendszer bizonyíthatósága a git commit belső szerkezetére épül. Minden commit **három önálló, de egymást erősítő rétegből** áll:

---

**① Tartalmi hash (SHA-256 digest)**

A commit tartalma (tree, author, message, timestamp) **determinisztikusan hash-elődik**:

```
commit_hash = SHA256(tree_hash + parent_hash + author + timestamp + message)
```

Azonos tartalom → azonos hash. Bármilyen egy-bites változtatás → teljesen más hash. Ez a **hamisíthatatlanság** alapja.

---

**② Láncolt hash (chained digest – a Merkle-elv)**

Minden commit tartalmazza az előző commit hash-ét (`parent`):

```
commit #N → parent: SHA256(commit #N-1)
                       └── parent: SHA256(commit #N-2)
                                      └── ...
```

Ez azt jelenti, hogy **egyetlen korábbi commit megváltoztatása az összes rákövetkező commit hash-ét érvényteleníti**. A lánc megbonthatatlan – a múlt nem írható át észrevétlenül.

---

**③ Digitális aláírás (GPG / Ed25519)**

A commit hash-t az aláíró **privát kulcsával** írják alá:

```
signature = Sign(privkey, commit_hash)
```

Az aláírás ellenőrzésekor a rendszer a nyilvános kulccsal verifikálja:

```bash
git verify-commit HEAD
# → gpg: Good signature from "CIC Relay Operator <relay@example.com>"
```

Az érvényes aláírás bizonyítja:
- **ki** hozta létre a commitot (identitás),
- **mikor** (a timestamp a hash részét képezi),
- és hogy a tartalom **nem módosult** az aláírás óta.

---

**④ Az aláíró PEM-je (nyilvános kulcs tanúsítvány)**

Az aláíráshoz használt kulcs nyilvános fele **PEM formátumban exportálható**:

```bash
gpg --armor --export <kulcs_ID> > relay-operator.pub.pem
```

Ez a PEM a **trust-anchor**: a rendszer ezen keresztül köti össze az identitást, a commitot és a ProofTrace-eseményt. A CIC kulcskezelési szabálya szerint a privát kulcs **kizárólag Vault vagy HSM alapon tárolható** – fájlba mentés tilos.

```
PEM → nyilvános kulcs → aláírás verifikáció → commit → ProofTrace → CommitRef
```

> *Nem az ember mondja, hogy igaz. A láncolat bizonyítja.*

---

**A demonstráció összefoglalása:**

| Fázis | Esemény | CIC bizonyítás |
|---|---|---|
| Terraform up | Infra létrejön | ProofTrace #1, CommitRef #1 |
| 5× kézi módosítás | Drift keletkezik | commit #2–#6, drift-log |
| Infra törlés | Hard Drift | HARD_DRIFT rögzítve |
| Rollback push | Intent deklarálva | OIS-ellenőrzés → Terraform apply |
| Infra újjáépül | Állapot visszaáll | Új ProofTrace, CommitRef visszautal #3-ra |

A teljes folyamat során **egyetlen állapotváltozás sem történt bizonyíték nélkül**. A rendszer nem az emberi ígéretre, hanem a kriptográfiai láncolatra alapozza a bizalmat.
