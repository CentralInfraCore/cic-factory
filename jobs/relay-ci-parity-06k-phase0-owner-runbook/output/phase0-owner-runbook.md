# #212 — A 0. fázis tulajdonosi előkészítési forgatókönyve (CIC_Relay #212, 8. lépés)

**Státusz: forgatókönyv (concept).** Ez a dokumentum parancsokat és beállításokat ír le; **egyiket sem hajtottam végre**, és a végrehajtása tulajdonosi lépés. A forgatókönyv megléte ≠ működik; a jóváhagyása ≠ elvégzett végrehajtás. A mérés, a kulcsművelet és az éles konfigurációmódosítás továbbra is HOLD.

## 1. Hogyan használd

- **Döntési alap:** a #82 (`7cf5dab`) K-1–K-8 ajánlásai, a tulajdonos elfogadásra javasolt döntései szerint: K-1…K-6 és K-8 ACCEPT, K-7 MEASURE. A forgatókönyv ezeket **nem módosítja**; ahol pontosít, jelöli.
- **Nevek (a tulajdonos javaslata):** szervezet `CIC-Security-Lab`; X repó `ci-adversarial-lab`; Y repó `ci-identity-lab`.
- **Mindegyik lépés** négy részből áll: **Parancs/beállítás** (a tulajdonos futtatja), **Hatás**, **Olvasó ellenőrzés** (futtathatom is, hitelesítő adat nélkül, nyilvános metaadatra, vagy te futtatod és beillesztheted), **Mit kapok vissza** (kizárólag nem titkos kimenet).
- **Hitelesítő adatot, kulcsot, tokent, gépi fiók jelszavát nem küldesz nekem.** A kanári érték értéktelen (O-5); ezt a kivételt a 4.5 lépés rögzíti.
- **Parancsváltozók** (egy shellben):

```bash
ORG=CIC-Security-Lab
X=ci-adversarial-lab
Y=ci-identity-lab
```

- **Platformviselkedés jelölése.** A parancsok szintaxisa és a hivatkozott beállítási útvonalak a platform dokumentációjából származnak; **ebben a sessionben nem futtattam őket, nem mért**. Ahol egy lépés a jelzett kimenetet nem adja, **állj meg és közöld**; ne találgass és ne kerüld meg. Ahol az olvasott érték „olvasott", azt ebben a sessionben csak olvasó lekérdezéssel olvastam.

## 2. Olvasott tények (csak olvasó lekérdezés, ebben a sessionben, 2026-11-22)

| # | Tény | Eredmény | Jelölés |
|---|---|---|---|
| T-1 | A `CIC-Security-Lab` név szabad-e | a szervezet- és a felhasználó-lekérdezés is `404 Not Found` | **olvasott**; a név a létrehozás pillanatában újraellenőrzendő (foglalható közben) |
| T-2 | `CIC_Relay` workflow-jogosultság alapértelmezése (K-4 (2)) | `default_workflow_permissions: write`, `can_approve_pull_request_reviews: true` | **olvasott** (csak olvasó API-hívás; a tulajdonos megerősíti az admin felületen) |
| T-3 | `CIC_Relay` fork-PR workflow jóváhagyási szabály (K-4 (1)) | `approval_policy: first_time_contributors` | **olvasott**; a tulajdonos megerősíti |
| T-4 | `CIC_Relay` engedélyezett akciók | `enabled: true`, `allowed_actions: all`, `sha_pinning_required: false` | **olvasott** |
| T-5 | K-4 (3): kap-e írási jogú tokent a fork-PR-ból induló workflow | **nincs olvasva** (az API nem adja; a felületen: Settings → Actions → General, „Fork pull request workflows") | **nyitott**: a tulajdonos olvassa |

**Megfigyelés a K-4-hez (nem döntés, nem módosítás):** a T-2 szerint a Relay alapértelmezett workflow-jogosultsága **írási**. Ez a K-4 alapján a Jel-2a prioritását érinti, és **külön biztonsági tétel**, nem a mérési terv része. **A forgatókönyv nem módosítja a Relay beállításait**; a tulajdonos dönt, hogy külön tételként kezeli-e (a 2FA-megfigyeléshez hasonlóan, #82 6. szakasz). A scratch mérési eredmény a Relay-re **nem általánosítható**.

## 3. A 0. fázis kapuja (G0) és a lépések sorrendje

A #82 5.1 szerint a **G0** feltételei: K-1 (szervezet, X repó), K-2, K-5, K-8, O-5 (a), a védett ág alapállapota (O-4 1.–2. sor kezdőértéke). A 0. fázis tartalma: a harness önellenőrzése (minden PK a tételek előtt), a kanárik elhelyezése, a mérési környezet rögzítése.

| Sor | Lépés | Döntés / kapu | Függ |
|---|---|---|---|
| **A** (G0, sorrend) | 4.1 szervezet → 4.2 X repó → 4.3 alapállapot-rögzítés → 4.4 kanári-környezet → 4.5 kanári-értékek → 4.6 workflow-csomag (nálam, külön GO) → 4.7 védett ág alapállapota → 4.8 G0 ellenőrzés | G0 | K-1, K-2, K-5, K-8, O-5 (a) |
| **B** (párhuzamos sáv, **nem** G0) | 5.1 Y repó → 5.2 két App kulcs nélkül (O-2a) → 5.3 gépi fiókok (O-3) → 5.4 kanári-pár (O-5b) → 5.5 O-4 szkriptek | G2, G3a | K-1, O-2a, O-3, O-5b, K-3 időpont |
| **C** (nem kapu) | 6 K-4 olvasás | — | — |

A B sor **nem előfeltétele** az A sornak (K-3 szerint nincs körkörös függés); az A sor eredménye önállóan jelenthető.

## 4. Az A sor — a G0 kapu lépései

### 4.1 A szervezet létrehozása (K-1, K-2)

- **Beállítás (webes felület):** `https://github.com/account/organizations/new` → Free csomag → név `CIC-Security-Lab` → tulajdonos: a saját fiókod. A kapcsolattartó e-mail a te választásod; **nem kerül hozzám, és nem kerülhet a repókba**. A szervezet létrehozása GitHubon nem végezhető API-val; a felület a kézi lépés.
- **Kezdő biztonsági beállítások (ajánlás, nem módosítja a #82-t):** Settings → Authentication security → a kétfaktoros hitelesítés megkövetelése a tagoknak. Settings → Member privileges → Base permissions: **No permission** (a gépi fiókok jogai így kifejezetten a repóra adottak). Indoklás: a gépi fiók A (írási jog) és B (nincs jog) szerepének élesen elkülönülnie kell (4.0, S2/S3).
- **Hatás:** új, üres szervezet; a meglévő `CentralInfraCore` érintetlen. A mérési szervezet külön, így az X repó beállításai nem közösek az éles repókkal (K-1 indoklása).
- **Olvasó ellenőrzés** (te futtatod, a kimenet nem titkos):

```bash
gh api "orgs/$ORG" --jq '{login, plan: .plan.name, two_factor_requirement_enabled, default_repository_permission}'
```

- **Mit kapok vissza:** a fenti kimenet. **Elvárás (a döntés szerint):** `plan` = `free`; a 2FA és az alap-jogosultság az általad választott érték (rögzítendő).
- **Visszafordítás:** a szervezet **nem törlendő** (a törlés HOLD, O-6); a repók archiválhatók. A 2FA-követelmény miatt a gépi fiókoknak (5.3) is be kell kapcsolniuk a kétfaktoros hitelesítést; ha ez nem megoldható, a követelményt a szervezeten ne kapcsold be, és ezt rögzítsd.

### 4.2 Az X repó létrehozása (`ci-adversarial-lab`, nyilvános) (K-1, K-2)

- **Parancs:**

```bash
gh repo create "$ORG/$X" --public --add-readme \
  --description "CIC 212 adversarial CI lab: canary values only, no real credentials"
```

- **Tartalmi szabály (K-2 korlát):** a repóba **nem kerülhet** személyes adat, éles azonosító, éles repó neve vagy valós titok. A README tartalma a repó leírása; ne írj bele mást. A commit-szerzői adat a mérési identitás.
- **Hatás:** üres, nyilvános repó egyetlen README-committtal; az Actions engedélyezett (alapérték).
- **Olvasó ellenőrzés** (nyilvános metaadat; én is futtathatom):

```bash
gh api "repos/$ORG/$X" --jq '{full_name, visibility, private, allow_forking, default_branch, archived}'
```

- **Elvárás:** `visibility` = `public`, `private` = `false`, `allow_forking` = `true` (a fork-PR esetekhez, M-B1; a K-2 előfeltétele), `default_branch` = `main`. Ha az `allow_forking` `false`, **állj meg és közöld** (az M-B1 külső fork-eseteinek előfeltétele; az ilyen eset INCONCLUSIVE lenne, #81).
- **Mit kapok vissza:** a kimenet.
- **Visszafordítás:** a repó archiválható; **törlés HOLD**.

### 4.3 Az alapállapot rögzítése (K-6, O-4 előtti állapot)

A mérés ellenőrzési alapja a **módosítás előtti állapot**; ezt a mérés minden beállítás-módosítása előtt rögzíteni kell. A következő lekérdezések **csak olvasnak**; a kimenet a factory job `raw/` alá kerül (K-8), ezért titokellenőrzéssel.

```bash
mkdir -p ~/.cache/ci-lab/baseline && cd ~/.cache/ci-lab/baseline
gh api "orgs/$ORG"                                   > org.json
gh api "repos/$ORG/$X"                               > repo-x.json
gh api "repos/$ORG/$X/actions/permissions"           > actions-permissions.json
gh api "repos/$ORG/$X/actions/permissions/workflow"  > actions-workflow-permissions.json
gh api "repos/$ORG/$X/actions/permissions/fork-pr-contributor-approval" > fork-pr-approval.json
gh api "repos/$ORG/$X/rulesets"                      > rulesets.json
gh api "repos/$ORG/$X/branches/main" --jq '{protected, name}' > branch-main.json
```

- **Hatás:** nincs változás; az X repó **alapállapota** rögzített (Actions-engedély, workflow-jogosultság, fork-jóváhagyás, szabálykészletek).
- **Mit kapok vissza:** a fájlok tartalma, miután futtattad rajtuk a titokellenőrzést:

```bash
grep -rEn 'ghp_|ghs_|gho_|github_pat_|BEGIN [A-Z ]*PRIVATE KEY' . || echo "no secret patterns"
```

- **Megjegyzés:** a `fork-pr-approval.json` végpontja a platform újabb része; ha `404`, a felületi állapotot rögzítsd (Settings → Actions → General → „Fork pull request workflows"), és írd le szövegesen.

### 4.4 A kanári-környezet (O-5 (a), E-6)

A kanári **ugyanazzal a tárolási hellyel és védelemmel** jön létre, mint amit a kibocsátó hitelesítő adata egy valódi telepítésben kapna (E-6; M-B1 elrendezése): **környezeti titok, az alapágra korlátozott ág-szabállyal**. Ehhez **nem kell App és nem kell az O-2**.

- **Parancs:**

```bash
ENVN=canary-issuer
gh api -X PUT "repos/$ORG/$X/environments/$ENVN" --input - <<'JSON'
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
gh api -X POST "repos/$ORG/$X/environments/$ENVN/deployment-branch-policies" -f name=main -f type=branch
```

- **Hatás:** a `canary-issuer` nevű környezet, amelyhez **csak az `main` ágról induló** futás fér hozzá.
- **Olvasó ellenőrzés:**

```bash
gh api "repos/$ORG/$X/environments/$ENVN" --jq '{name, deployment_branch_policy}'
gh api "repos/$ORG/$X/environments/$ENVN/deployment-branch-policies" --jq '.branch_policies[] | {name, type}'
```

- **Elvárás:** `custom_branch_policies` = `true`, egyetlen szabály: `main`. Ha a végpont eltér, a felületen állítsd be (Settings → Environments → `canary-issuer` → Deployment branches: *Selected branches* → `main`), és írd le.
- **Visszafordítás:** a környezet törölhető (`gh api -X DELETE …`); a törlés a repó archiválása előtt nem szükséges.

### 4.5 A kanári-értékek (O-5 (a))

Két **véletlen, értéktelen** érték:

| Név | Hely | Szerepe a mérésben |
|---|---|---|
| `CANARY_PROTECTED` | a `canary-issuer` környezet titka (4.4) | a **védett konfiguráció**; (J) ismert jó kontroll az M-B1/M-B2 PK-jában (a kanári nem olvasható a PR-ból induló futásban) |
| `CANARY_UNRESTRICTED` | az X repó szintű titka, korlátozás nélkül | az **ültetett (U)** kontroll: ismerten hozzáférő konfiguráció, amelyet a harness olvas (M-B1 PK (U)) |

- **Parancs:**

```bash
umask 077; mkdir -p ~/.cache/ci-lab
P="CANARY-212-$(openssl rand -hex 16)"
U="CANARY-212-$(openssl rand -hex 16)"
printf '%s\n' "CANARY_PROTECTED=$P" "CANARY_UNRESTRICTED=$U" > ~/.cache/ci-lab/canary-X.txt
printf '%s' "$P" | gh secret set CANARY_PROTECTED    --env "$ENVN" --repo "$ORG/$X"
printf '%s' "$U" | gh secret set CANARY_UNRESTRICTED               --repo "$ORG/$X"
```

- **Szabály:** az értékeket **véletlenül kell előállítani, és sehol máshol nem szabad használni** (E-1: a kanári és a valódi hitelesítő adat nem fedi át egymást; a kanári soha nem azonos egy valódi értékkel). A `CANARY-212-` előtag a kiszivárgás-észlelés azonosítója.
- **Olvasó ellenőrzés** (csak nevek és időbélyegek, érték nem):

```bash
gh secret list --env "$ENVN" --repo "$ORG/$X"
gh secret list --repo "$ORG/$X"
```

- **Mit kapok vissza:** a két lista (nevek), és **a két kanári értéke** a `~/.cache/ci-lab/canary-X.txt` fájlból. **Ez az egyetlen kivétel a „nem küldesz titkot" szabály alól:** a kanári **értéktelen** (a #82 O-5 szerint nem titok a számomra); az észleléshez a harnessnek ismernie kell, hogy mit keressen a naplókban és artifactokban. Ha mégsem akarod megadni az értéket, a harness csak az `CANARY-212-` előtagra és a hossz-mintára tud keresni, ami gyengébb észlelés (ezt az eredményekben jelölni kell).
- **Visszafordítás:** a titkok törölhetők (`gh secret delete`); a fájl törlendő a mérés lezárásakor.

### 4.6 A 0. fázis workflow-csomagja (nálam, külön GO és review)

A harness önellenőrzéséhez és az első mérési PR-okhoz workflow-fájlok kellenek az X repón (a megkövetelt check neve, a kanári-olvasó és a PK-kontrollok). **Ezt a csomagot nem ez a PR készíti el:** külön, review-köteles munkacsomag, **külön GO-val**, mert tartalmazza a check nevét, amelyre a 4.7 védett ág hivatkozik. Az X repóba **a tulajdonos pusholja** (K-8).

- **Hatás ebben a forgatókönyvben:** semmi; a lépés azt rögzíti, hogy a 4.7 paramétere (`CHECK_NAME`) ebből a csomagból származik.
- **Ha eltérnél a sorrendtől:** a védett ágat a 4.7-ben **a workflow létrejötte előtt** is beállíthatod; ebben az esetben a megkövetelt check még nem létezik, és az ág nem mergelhető, amíg az első futás a nevet nem létrehozza.

### 4.7 A védett ág alapállapota (O-4 1.–2. sor kezdőértéke)

Ez a **beállítás-módosítás**, amelyet a #82 O-4 a tulajdonos repólétrehozáskori lépéseként ír elő; a mérés közbeni váltások (a `strict` ki/be az M-A3 (2)-ben) szkriptesek, külön.

- **Paraméterek (a tulajdonos dönt, rögzítendő):**
  - `CHECK_NAME`: a 4.6 csomag szerint (addig helyőrző).
  - `strict` (a frissesség-megkövetelés kezdőállapota): **javasolt kezdőérték `false`**, mert az M-A3 (2) pont ezt kapcsolja be a méréskor, a kezdőállapot ezért a „ki".
  - `enforce_admins`: **javasolt `true`**, hogy a védelem az adminokra is érvényes legyen; **az S1 szerep csak beállít, nem mér és nem PR-szerző** (#82 4.0). A tényleges érték rögzítendő a mérés előtt.
- **Parancs:**

```bash
CHECK_NAME=lab-gate   # placeholder: replace with the name from the 4.6 workflow package
gh api -X PUT "repos/$ORG/$X/branches/main/protection" --input - <<JSON
{
  "required_status_checks": {"strict": false, "contexts": ["$CHECK_NAME"]},
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
```

- **Hatás:** az `main` ág védett: a megadott check megkövetelt, a frissesség nem; az adminokra is érvényes.
- **Olvasó ellenőrzés:**

```bash
gh api "repos/$ORG/$X/branches/main/protection" --jq '{required_status_checks: .required_status_checks, enforce_admins: .enforce_admins.enabled}'
```

- **Mit kapok vissza:** a kimenet; a rögzített kezdőérték (`strict`, `enforce_admins`, a check neve).
- **Visszafordítás:** `gh api -X DELETE "repos/$ORG/$X/branches/main/protection"`. A változtatás **előtt** rögzítsd az alapállapotot (4.3).

### 4.8 G0 ellenőrzés

A G0 teljesülésének **olvasó ellenőrzése** (én is futtathatom a nyilvános részére; a többit te):

| # | Feltétel (#82 5.1) | Ellenőrzés | Kimenet |
|---|---|---|---|
| 1 | K-1: szervezet és X repó létezik | 4.1, 4.2 olvasó parancsa | `login`, `full_name` |
| 2 | K-2: nyilvános | 4.2 | `visibility = public` |
| 3 | K-5: 300 futás korlát elfogadva | nem parancs | a tulajdonosi elfogadás szövege |
| 4 | K-8: a push-t a tulajdonos futtatja, nincs hitelesítő adat nálam | nem parancs | a tulajdonosi elfogadás |
| 5 | O-5 (a): kanáriértékek a védett és a nem védett helyen | 4.5 `gh secret list` | két név, két hely |
| 6 | védett ág alapállapota rögzítve | 4.7 | `strict`, `enforce_admins`, check neve |
| 7 | az alapállapot-fájlok elkészültek és titokellenőrzöttek | 4.3 | a titokellenőrzés kimenete |

**A G0 teljesülése után** a 0. fázis a harness önellenőrzésével indul (minden PK külön, a tételek előtt). **Az indulása külön GO**, ez a forgatókönyv nem indítja el.

## 5. A B sor — párhuzamos előkészítés (O-2a, O-3, O-5b, Y repó)

A #82 K-3 szerint ez a sor **nem előfeltétele** a G0-nak, és **nem is a G0 része**. A tulajdonos tervezett időpontot ad rá (K-3 előfeltétele); ha nincs, a 2. és 3a–3b fázis **nem indul**, a 0–1. fázis eredménye önállóan jelentendő.

### 5.1 Az Y repó (`ci-identity-lab`) — a G3a kapuhoz

```bash
gh repo create "$ORG/$Y" --public --add-readme \
  --description "CIC 212 identity lab: two App identities, canary pair, benign PRs only"
gh api "repos/$ORG/$Y" --jq '{full_name, visibility, allow_forking, default_branch}'
```

- **Szabály (E-2):** az Y repóban **ellenséges PR akkor sem fut, ha nincs valódi kulcs**: a 3b PR-jai jóindulatúak, az ellenséges viselkedést a tulajdonos futtatta, az App saját tokenjével végzett API-hívások jelentik.
- **Szabály (E-3):** az Y repón **alapértelmezésben nincs kulcs GitHub-titokként**.

### 5.2 A két App kulcs nélkül (O-2 (a), a G3a kapuhoz)

Webes felület: a szervezet → Settings → Developer settings → GitHub Apps → *New GitHub App*. **Két App**, a következő beállításokkal:

| Mező | Kibocsátó App | Verifier App |
|---|---|---|
| Név | `cic-lab-issuer` (javaslat; a név a tiéd) | `cic-lab-verifier` (javaslat) |
| Webhook | **Active: ki** (nincs esemény) | **Active: ki** |
| Repository permissions | Checks: **Read and write**; Contents: **Read-only**; Metadata: **Read-only** | ugyanez |
| Egyéb jogosultság | **nincs** | **nincs** |
| Where can this App be installed | **Only on this account** | **Only on this account** |
| Telepítés | **csak az Y repóra** (*Only select repositories*) | **csak az Y repóra** |
| **Privát kulcs** | **NE generálj** (*Generate a private key* gomb: **ne kattints rá**) | **NE generálj** |

- **Olvasó ellenőrzés:** a kulcs hiánya az App oldalán olvasható (*Private keys* üres). Programmatikusan nyilvános metaadat nem adja; a tulajdonos olvassa a felületen.
- **Mit kapok vissza:** az App-ok **azonosítója** (App ID, nem titok) és a telepítések azonosítója; **kulcs nem**.
- **Szabály (E-3, E-4):** a valódi privát kulcsot a tulajdonos **csak a 3b fázisban** hozza létre (O-2 (b)), a saját gépén őrzi, és a 3b végén visszavonja (O-6). **Ez a forgatókönyv a 3b-t nem tartalmazza.**
- **Megjegyzés:** a meglévő `cic-integrity-scratch` App (ID 5852604) **nem érintett**; ezek új App-ok.

### 5.3 A két gépi fiók (O-3) — a G2 kapuhoz

| Szerep | Fiók | Jogosultság | Megjegyzés |
|---|---|---|---|
| S2 | gépi fiók **A** | **külső együttműködő `write` szerepkörrel az X és az Y repón**; **nem** tulajdonos, **nem** admin, **nem** maintain | belső (azonos repón lévő ágról induló) PR-ok |
| S3 | gépi fiók **B** | **nincs** jogosultság | fork-PR-ok |

- **Szabály:** a **tulajdonos saját, admin jogú identitása sosem PR-szerző** (S1).
- **Platformszabály:** a gépi fiókok használatára a platform szolgáltatási feltételei külön korlátozást szabhatnak; **ezt a tulajdonos ellenőrzi, én nem állítom**. Ha nem megoldható, a fork-esetek INCONCLUSIVE-ok (#81 M-B1), és az írási jogú szerepet egy másik, nem admin személy tölti be.
- **Jelszó, token, SSH-kulcs a fiókokhoz nem kerül hozzám.** A PR-okat a tulajdonos futtatta push-szkript hozza létre (K-8).
- **Olvasó ellenőrzés:** a jogosultságok olvashatók a szervezet admin nézetéből (`gh api "repos/$ORG/$X/collaborators/<account-A>/permission"`, az eredmény `write`, nem `admin`); a fiók neve nem titok.
- **Mit kapok vissza:** a két fiók **nyilvános neve** és a jogosultság-kimenet.

### 5.4 A kanári-pár (O-5 (b)) — a G3a kapuhoz

Az Y repón **két kanári**, a későbbi valódi kibocsátó- és verifier-kulcs tárolási helyén (E-6; M-D5): két külön környezet (`canary-issuer-y`, `canary-verifier-y`), mindkettő az `main` ágra korlátozva, **külön** a másiktól. A parancsok a 4.4–4.5 mintát követik az Y repóra, **két** környezettel és két értékkel. **Valódi kulcs ekkor még nem létezik** (E-4).

### 5.5 Az O-4 szkriptek (G2/G3a)

A beállítás-módosító szkriptek (a #82 O-4 9 sora) **az én feladatom elkészíteni, külön GO-val és review-val**; a tulajdonos futtatja őket, a hitelesítő adatával, amelyet én nem látok. Ez a forgatókönyv azokat **nem** tartalmazza, mert tartalmuk a mérési tételek elrendezésétől függ (K-6 zárt lista).

## 6. C sor — K-4 olvasás

A K-4 szerint a tulajdonos **csak olvassa és közli** a `CIC_Relay` három Actions-beállítását; **módosítás nincs**.

| # | Beállítás | Értéke (olvasott, 2. szakasz) | A tulajdonos teendője |
|---|---|---|---|
| (1) | A fork-PR-ból induló workflow-k jóváhagyási szabálya | `first_time_contributors` | megerősíti az admin felületen |
| (2) | Alapértelmezett workflow-jogosultság | `write` | megerősíti |
| (3) | Kap-e írási tokent a fork-PR-ból induló workflow | **nincs olvasva** | olvassa és közli |

A felületi útvonal: `CIC_Relay` → Settings → Actions → General. **A (2) érték a Relay-re vonatkozó külön biztonsági megfigyelés (2. szakasz); itt nem módosítjuk.**

## 7. Leállási feltételek

A 0. fázis és a B sor végrehajtása közben **azonnal állj meg és közöld**, ha:

- a kanári érték **a mérési kereten kívül** megjelenik (a #81 2.5);
- bármelyik lépés az éles `CentralInfraCore` szervezetet, a `CIC_Relay`-t vagy egy éles beállítást **módosítaná**;
- egy App privát kulcs jönne létre a 3b előtt, vagy egy valódi kulcs az X vagy Y repó titkai közé kerülne (E-1, E-3, E-4);
- egy parancs eltérő kimenetet ad a jelzettnél (az eltérést **ne** oldd meg önkényesen);
- az `allow_forking` `false` az X vagy Y repón.

## 8. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `CIC-Security-Lab` név a lekérdezéskor szabad volt | olvasott | 2. szakasz T-1 (a szervezet- és a felhasználó-lekérdezés `404`) | a 4.1 létrehozáskor a név újraellenőrzendő | a név közben foglalt lehet |
| A Relay alapértelmezett workflow-jogosultsága írási; a fork-PR jóváhagyási szabálya `first_time_contributors` | olvasott | 2. szakasz T-2, T-3 (csak olvasó API-hívás) | a tulajdonos megerősíti az admin felületen | a (3) pont (írási token a fork-PR-nak) nincs olvasva |
| A parancsok az itt leírt hatást adják | concept (dokumentált platformviselkedés, ebben a sessionben **nem ellenőrzött**) | a platform dokumentációja; nincs futtatás | minden lépés olvasó ellenőrzéssel zárul; eltérésnél leállás (7. szakasz) | az API-végpontok eltérhetnek; a felületi alternatíva jelölve |
| A forgatókönyv nem módosítja a #82 K-1–K-8 ajánlásait | concept | a 1. szakasz; a pontosítások jelölve (a `strict`/`enforce_admins` kezdőérték javaslat, a kanári-érték átadása) | tartalmi review | a tulajdonos a javaslatoktól eltérhet; az eltérést rögzíteni kell |
| A 0. fázis (G0) az O-2a, O-3, O-5b nélkül is nyitható | concept (következtetés a #82 K-3/E-5-ből, nem mért) | 3. szakasz A/B sor; #82 K-3 | a 0–1. fázis mérése közben derül ki | ha egy tétel mégis igényli a második identitást, a függés későn derül ki |
| A kanári az éles kulccsal azonos védelmű tárolási helyen reprezentálja a kulcs csatornáit | **következtetés, nem mért** | #81 2.5 és E-6 | a 0. fázis dokumentálja a kanári elhelyezését | a kanári a konfigurációt méri, nem a kulcsot (E-6) |
| A kanári értékek megadása nekem értéktelen adat átadása | concept | 4.5 szabály; #82 O-5 | a tulajdonos megerősíti, hogy az érték véletlen és nem használt máshol | ha az érték mégis valós, kiszivárgás (E-1) |
| Nincs hitelesítő adat, kulcs vagy token átadás nekem | concept (tervezési tulajdonság) | 1. szakasz; 4.5, 5.2, 5.3 | a tulajdonos soha nem küld ilyet; a `raw/` titokellenőrzés (4.3) | a titokellenőrzés mintái nem teljesek |
| A mérés, a kulcsművelet és az éles konfigurációmódosítás nem történt meg | igaz a forgatókönyv elkészítéséig | nincs írási művelet a környezeten; az egyetlen környezeti tevékenység olvasó lekérdezés (2. szakasz) | `git log`, a tulajdonos futtatási jegyzete | — |

## 9. Mit nem állít ez a dokumentum

- **Nem állítja,** hogy a parancsok működnek; egyiket sem futtattam (a forgatókönyv megléte ≠ működik).
- **Nem állítja,** hogy a platform viselkedése a leírt, mert a hivatkozott beállítások dokumentáltak, ebben a sessionben nem ellenőrzöttek.
- **Nem hoz döntést** a tulajdonos helyett: a nevek, a kezdőértékek (`strict`, `enforce_admins`), a 2FA-követelmény és az Y/B sor időpontja a tulajdonos döntése.
- **Nem tartalmazza** a 3b fázist, a valódi kulcsok létrehozását, az O-1 felfüggesztési ablakokat, az O-4 szkripteket és a 4.6 workflow-csomagot; ezek külön GO-t és review-t igényelnek.
- **Nem módosítja** a Relay vagy az éles szervezet beállításait; a T-2 megfigyelés külön biztonsági tétel.
- **Nem általánosít** a scratch eredményről a Relay-re, és nem jelent mérési eredményt.
