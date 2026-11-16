# relay-ci-parity-06b-pin-protection — jelentés (CIC_Relay #195, PR #201)

Nyelv: magyar. Minden állítás mellett a bizonyíték helye; ami nincs mérve, az így van jelölve.

## 1. Vizsgált állapot

| Tétel | Érték |
|---|---|
| CIC_Relay `main` (indulás) | `ae8eccc126ba74a77b9a96e4b99816c046ba750f` (a PR-06 `c18fef2` és a #199 után; a klón tiszta volt: `git status --short \| wc -l` = 0 a klónozás után) |
| Megvalósítás | **#201** `feature/relay-ci-parity-06b-pin-protection`, fej **`6f7aabb282f26d882713c1fed9c559cccf89dcd8`** (története: `55c077a` → `b8a132c` → `6f7aabb`), `--base main`, **nem mergelve** |
| cic-factory `main` | `103bee0a0a3bd59861c6b2352758f5e1efda3211` (a #69 spec merge-commitja) |
| Spec | cic-factory #69 (`jobs/relay-ci-parity-06b-pin-protection/input.md`), a review F1 és F2 pontjaival |

A bizonyító PR-ek (mind draft, `[DO NOT MERGE]`, nyitva): #202 `pin-update`, #203 `tool-removed`, #204 `forged-sha`, #205 `weakened-script`, #206 `bootstrap-forced`, #207 `step-removed`; ellenpróbák: #208 `r-pin-update`, #209 `r-tool-removed`, #210 `r-weakened-script` (a #208–#210 a befagyasztott, mechanizmus nélküli `base-old` ágra mutat: `ae8eccc`). A fejek és a teljes check-lista: `raw/checks.tsv`.

**A klón tisztasága:** a klón a klónozáskor tiszta volt. A munka közben egy ismeretlen háttérfolyamat a követett `.yaml` fájlokat módosította (a PR-05 óta ismert, az ok továbbra sem megállapított). Egy proof-generátorom `git add -u`-ja ezeket felvette egy ágra, ezt észleltem és tiszta ágakkal újraépítettem; minden végleges ágon **0 `.yaml` fájl** van a diffben (a generátor azóta explicit fájllistával ad hozzá).

## 2. Összefoglaló

- **A mérési referencia védett:** pull requestnél a pinek, a `surfaces` és az `approvers` a **base ág csúcsából** jönnek, és a `check-tools` is a base-ről futó `quality_gate.py`-ból fut; a referencia-commit és -digest a check kimenetében szerepel. **Mind a 14 hívóhely** (12 `check-tools`, 2 `object-evidence`) a referencián át megy; egy teszt rögzíti a 14-et.
- **A jogos pin-frissítés atomi** és **HEAD- és digest-kötött tulajdonosi jóváhagyáshoz** kötött; új push érvényteleníti. A jóváhagyás nem kerüli meg a kapukat (a #202 jóváhagyott állapotában minden kapu teljes erővel futott az új pinnel).
- **A hat kötelező negatív eset** (review F2) valós GitHub Actions futással bizonyított, kivéve a workflow-lépés eltávolítását, amely **védelmi résként reprodukált** (#207).
- **A mérési referencia védelme és a mérési kötelezettség kikényszerítése két külön feladat.** Az elsőt ez a PR megoldja; a másodikhoz olyan ellenőrzési mechanizmus kell, amelyet a vizsgált PR nem módosíthat (repository-szintű). Ez a **bizonyított, nyitott rés**, nem ennek a PR-nek a hatóköre.
- Nincs új küszöb, nincs toolchain-csere, nincs termékkód; a repó-beállításokhoz nem nyúltam.

## 3. A megoldás

| Pont | Mit tesz | Hol |
|---|---|---|
| A. Referencia a base-ből | a base ág csúcsát lekéri; a pin, `surfaces`, `approvers` onnan; a `check-tools` scriptje onnan fut (`baseline-guard` minta) | `.github/actions/measurement-reference/action.yml`, `scripts/quality_gate.py pin-reference` |
| B. Atomi frissítés | a megváltozott pin-fájl csak jóváhagyással elfogadott; jóváhagyással a **fej pinje** a referencia, és minden kapu azzal fut | `pin_reference()`, `find_approval()` |
| C. Hamis referencia | a megadott base SHA csak akkor érvényes, ha a base ág commitja (`[REFERENCE_FORGED]`) | `pin_reference()` |
| D. A referencia rögzítése | a check kiírja a referencia-commitot és -digestet; eltérő pin-fájlnál `[REFERENCE_MISMATCH]`; hiányzó/olvashatatlan referencia fail closed | `verify_reference_record()`, `check-tools --reference` |
| Nem PR esemény | a fa maga a referencia (`SELF_REFERENCE`), a rekord kimondja | `--mode push` |
| Bootstrap | csak a mechanizmust bevezető változásnál; ha a base már hordozza, `[BOOTSTRAP_REFUSED]` | `--mode bootstrap` |

**A jóváhagyás formája:** a base pin-fájl `approvers` listájában szereplő felhasználó PR-kommentje: `APPROVE-MEASUREMENT-TOOLS head=<40 hex> digest=sha256:<64 hex>`. Nem commit (a spec kikötése: nem az ellenőrzött PR állítja elő), a GitHub hitelesíti a szerzőt, és a fejhez/digesthez kötött, ezért új push érvényteleníti. **PR-review nem használható**, mert a saját PR-ját a tulajdonos nem approve-olhatja. Az `approvers` lista a **base** fájlból jön: a PR nem veheti fel magát (egységteszt).

## 3b. Reachability: a védelem tényleg be van kötve (file:line)

A státusz nem a script vagy a teszt létezéséből következik: a hívási út a #201 fején (`6f7aabb`), `git grep` kimenete a `raw/reachability.txt`-ben.

- **A composite action** (`.github/actions/measurement-reference/action.yml`) **13 helyen** hívott a workflow-kban (`uses: ./.github/actions/measurement-reference`): `verify.yml`, `mutation-pr.yml`, `mutation.yml`, `nightly.yml`, `gate-selftest.yml`, `object-evidence.yml` (a pontos sorok a raw fájlban).
- **A referencia felhasználása:** a `"${MR_GATE:?…}"` és `"${MR_PINS:?…}"` kifejezés **26 sorban** szerepel a workflow-kban (a 12 `check-tools` hívás 2-2 soron, az `object-evidence` `--tool-pins` két hívása); egy teszt (`test_no_workflow_reads_the_pins_or_the_checking_script_from_the_working_tree`) rögzíti a 14 hívóhelyet.
- **Az action hívja a scriptet:** `action.yml:28` (`pin-reference --mode push`) és `action.yml:47` (`python3 "$GATE" pin-reference --mode "$MODE" …`); a base scriptjének kiválasztása `action.yml:36`; az env kivezetés `action.yml:51-53`.
- **A script függvényei:** `find_approval` `quality_gate.py:793`, hívója `:905` (a `pin_reference()`-ben); `pin_reference` `:806`, hívója `cmd_pin_reference` `:935`; `cmd_pin_reference` `:934`, regisztrálva `:1090`; `verify_reference_record` `:954`, hívója `cmd_check_tools` `:994`; a CLI `pin-reference` `:1073`.
- **Egy dead-code jellegű eset nincs:** minden függvénynek van production hívója, és mind a 14 hívóhely a referencián át megy. A hívás **futását** a 4. szakasz valós Actions-naplói bizonyítják.

## 4. Bizonyítékok (valós GitHub Actions futás)

| Tulajdonság | PR (fej) | Eredmény | Bizonyíték |
|---|---|---|---|
| **Jogosulatlan pin-módosítás** | #202 (`5faef9d`) | a referencia-lépés `[PIN_CHANGED_UNAPPROVED]`-del buk, digest `cd3ecb0e…` → `72cb9857…` | a `5faef9d` jóváhagyás nélküli első futásának naplóit olvastam (6 job `PIN_CHANGED_UNAPPROVED`), de **nem mentettem a `raw/`-ba**; a mentett, azonos okú bizonyíték a későbbi fejé: `raw/202-stale-reasons.txt` (a pin-fájl változatlan, csak a fej más) |
| **Jogosult pin-módosítás** | #202 (`5faef9d`, a komment után) | **27/27 zöld**, `pin reference: APPROVED_UPDATE reference-commit=6f7aabb… reference-digest=sha256:72cb9857…`; a `cargo-mutants` 27.0.0 a mutációs jobokon végigfutott | `raw/202-approved-runs.tsv` (attempt 3), `raw/202-approved-reference-lines.txt` (7 sor) |
| **Jóváhagyás elévülése** | #202 (`5c81dbc`) | egy, a pin-fájlt nem érintő commit (`PROOF-PUSH-AFTER-APPROVAL.txt`) után ismét piros, `[PIN_CHANGED_UNAPPROVED]`, miközben a komment (id 6930979560) a PR-en van | `raw/202-stale-reasons.txt`, `raw/approval-comment.txt`, `raw/checks.tsv` |
| **Mérési felület védelme** | #203 (`56490cd`) | `cargo-mutants` kivéve a `mutation-rust` felületről és a jobok deklarációiból: `[PIN_CHANGED_UNAPPROVED]`, 8 piros job | `raw/203-reasons.txt` |
| **Referencia hitelessége** | #204 (`6bf9465`) | a PR-fej SHA-ja base SHA-ként: `[REFERENCE_FORGED] … is not a commit of the base branch` | `raw/204-reasons.txt` |
| **Verifikátor integritása** | #205 (`08bc02b`) | a `tool_pin_findings` mindent elfogad a PR scriptjében, a job Go-ja go1.26.10, a pin go1.26.11: **a `coverage` job piros**, `[TOOL_UNUSABLE] 'go' was 'go1.26.10', the pinned version is 'go1.26.11'`: a base scriptje fut | `raw/205-coverage-job.txt` |
| **Bootstrap védelme** | #206 (`1b2d890`) | erőltetett bootstrap: `[BOOTSTRAP_REFUSED] the base already has the pin reference mechanism` | `raw/206-reasons.txt` |
| **Ellenőrzés eltávolítása** | #207 (`1bb8004`) | **minden check zöld (13 sikeres, 2 kihagyott, 0 piros)**; a `coverage` jobban a referencia-lépés és a check **hiányzik**, a job `go version go1.26.10`-et használ, miközben a pin go1.26.11 | `raw/207-coverage-job.txt`, `raw/checks.tsv` |
| **Ellenpróba: pin** | #208 (`a323d52`) | a mechanizmus nélküli bázison ugyanaz a `cargo-mutants` 27.0.0 pinváltás **27/27 zöld** | `raw/checks.tsv` |
| **Ellenpróba: eszközeltávolítás** | #209 (`5a97903`) | a mechanizmus nélküli bázison a kötelező eszköz eltávolítása **27/27 zöld** | `raw/checks.tsv` |
| **Ellenpróba: verifikátor** | #210 (`f868f66`) | a **célzott kapu átengedi** a módosítást (`coverage` job: `tools pinned (coverage-go): go=go1.26.10`, a pin go1.26.11), de a **teljes CI 24/27** (3 piros: `python`, `object-evidence`, `verify`), tehát **a teljes pipeline nem zöld** | `raw/210-coverage-job.txt`, `raw/checks.tsv` |

**A #210 pontos olvasata (a review kérésére):** a coverage kapu valóban átengedte a gyengített ellenőrzést; a másik három bukás miatt a pipeline összességében nem zöld, ezért az ellenpróba nem „27/27". A bukások okai: a `python` és az `object-evidence` a gyengített checker saját tesztjei és seeded esetei (a PR ezeket szerkeszthetné, ezért csak részleges második védvonal), a `verify` pedig a `govulncheck` standard library sérülékenysége a go1.26.10-en, ami független a védelemtől.

## 5. A spec review pontjainak teljesülése

| Pont | Állapot | Bizonyíték |
|---|---|---|
| F1: atomi frissítés, HEAD- és digest-kötött jóváhagyás, teljes ellenőrzés, új push érvényteleníti | teljesült | #202 három állapota |
| F2: pin, eszköz eltávolítása, hamis SHA, script gyengítése, workflow-lépés eltávolítása, jóváhagyás utáni push | teljesült, a workflow-lépésnél **dokumentált, reprodukált rés** | #202–#207 |
| Kikötés: a jóváhagyási rekord nem lehet ugyanabban a commitban, és nem állítható elő a PR által | teljesült: külső, GitHub által hitelesített komment | `raw/approval-comment.txt` |

## 6. Amit menet közben találtam (hibák, tanulságok)

- **A jóváhagyó komment CRLF sorvéggel tárolódik** (`…7424\r\n\n`), és az első verzió regexe csak szóközt/tabot engedett a digest után: a **valódi jóváhagyás nem volt elfogadva**. Az egységteszt `\n`-nel futott, ezért nem látta; a valódi komment hozta felszínre. Javítva (`6f7aabb`), teszttel; a sor belsejében lévő `\r` továbbra sem jóváhagyás.
- **A `rust` job a PR merge-refjét sekélyen tölti le**, a PR-fej commit nem volt a checkoutban: a referencia-lépés fail closed buk, de `PIN_DELETED`-et jelzett. Javítva (`b8a132c`): a fej lekérése, és a hiányzó commit `REFERENCE_INVALID`.
- **A Go verzióját nem a `setup-go`, hanem a `go.mod` `toolchain` sora (alsó korlát) és a `GOTOOLCHAIN` dönti el**; az első proofok hatástalan módosítást használtak (a Go nem változott), ezért újraépítettem őket `GOTOOLCHAIN`-nel. Ugyanígy az első `pin-update` proof go1.26.10-re lépett vissza, amelyen a `govulncheck` jogosan bukott: ez nem a védelem, hanem egy sérülékeny verzióra váltás eredménye, ezért a jogos frissítés bizonyítása a `cargo-mutants` 27.1.0 → 27.0.0 ártalmatlan váltására került.
- **A wiring-tesztek (`python` job) a `step-removed` és a `tool-removed` manipulációt is elkapták**: a második védvonal létezik, de a PR szerkesztheti, ezért a proofok a saját teszttáblájukat is konzisztensre szerkesztik, ahogy egy valódi manipuláció tenné.
- **Saját hiba:** a proof-generátorom `git add -u`-ja a háttérfolyamat által módosított `.yaml` fájlokat is felvette egy ágra, és egy félresiklott futás egy ágat hibás tartalommal hozott létre; észleltem, tiszta ágakból újraépítettem, a generátor azóta explicit fájllistát és tisztaságellenőrzést használ.

## 7. Korlátok (mért vagy kimondott)

- **A #207 rés (mért):** pull requestnél a workflow-fájlok és a composite action **maguk is a PR-ből jönnek**, ezért a PR törölheti a referencia-lépést és a `check-tools` hívást; a `baseline-guard` ugyanezt a korlátot hordozza. A rés **reprodukált**, nem következtetés.
- **A `BOOTSTRAP` mód** egyszeri, a bevezetésre szolgál: a script a base-ből ellenőrzi, hogy a base még nem hordozza a mechanizmust, és ha igen, elutasít (#206). **Mérési korlát:** ha a PR a `GATE` kiválasztását is a saját scriptjére cseréli, az ugyanaz a rés-osztály (a PR irányítja, melyik script fut).
- **`object_model.py`:** a pinek a referenciából jönnek, de maga a verifier a PR-ből fut (nem a base-ből): ez a #207-tel azonos osztály.
- **`mutation.yml` és `nightly.yml`** (ütemezett) check-lépései PR-ben nem futnak; **nem mért futással**, csak szöveggel és egységteszttel fedettek (`SELF_REFERENCE` ág).
- **A `approvers` lista** egyetlen bejegyzést (`sinkog`) tartalmaz; hogy ez a kívánt jóváhagyó fiók-e, a tulajdonos dönti el (nem ellenőriztem, csak a PR-eken látható login).
- **A review „aláírt toolchain-update PR" javaslatából** a commit-aláírás kikényszerítése **nincs megvalósítva**: a Relay-ben nincs aláírás-ellenőrző kapu (a v1 hook fut, nincs verifier); a jóváhagyás a hitelesített komment, nem a commit-aláírás.
- **A `cargo-mutants` és a `cargo-llvm-cov` telepítési pinje** (`taiki-e/install-action`) továbbra is külön tétel (a `cargo-llvm-cov` verziója telepítéskor a legfrissebb; a pin-fájl szerinti eltérés a kapukat pirosra váltja).
- **Idő és költség:** a CI-futások ideje nem lett külön mérve.

## 8. Claim-evidence tábla

| Állítás | Státus | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A pin a base-ből olvasódik pull requestnél | mért | #202–#210 naplói: `pin reference: UNCHANGED/APPROVED_UPDATE reference-commit=<base>` | valós Actions-napló | az action a PR-ből jön (#207) |
| Jogosulatlan pinváltás elutasított | mért | `raw/202-stale-reasons.txt`, `raw/203-reasons.txt` | valós futás, ellenpróbával (#208, #209) | alacsony |
| Jogosult, atomi frissítés átmegy, teljes kapuval | mért | `raw/202-approved-*` (27/27) | valós futás | az approver a base listából jön |
| A jóváhagyás elévül új pushra | mért | `raw/202-stale-reasons.txt` | valós futás, azonos pin-fájl | alacsony |
| Hamis referencia-SHA elutasított | mért | `raw/204-reasons.txt` | valós futás | alacsony |
| A base scriptje fut, a PR gyengített scriptje nem | mért | `raw/205-coverage-job.txt` vs `raw/210-coverage-job.txt` | párhuzamos futás védelemmel és anélkül | a PR a hívást törölheti (#207) |
| A bootstrap nem megkerülési út | mért (a script szintjén) | `raw/206-reasons.txt` | valós futás | a PR a script választását is átírhatja (rés-osztály) |
| Az ellenőrzés eltávolítása nem védett | **mért: rés** | `raw/207-coverage-job.txt` | valós futás | nyitott, repository-szintű |
| A CRLF-es jóváhagyás elfogadott | mért | `6f7aabb`, a #202 27/27 | valós komment, valós futás | alacsony |
| A #201 27/27 zöld a `6f7aabb`-en | mért | `raw/checks.tsv` | GitHub Actions | alacsony |
| Nincs új küszöb, toolchain-csere, termékkód | olvasott (diff) | a #201 diffje: workflow-k, `scripts/`, `tests/`, `.measurement-tools.json` | diff-olvasás | alacsony |

## 9. Nyitott döntések

1. **A workflow-integritás kikényszerítése** (a #207 rés): a PR által nem módosítható ellenőrzési mechanizmus (required workflow / repository ruleset / a base workflow-ját futtató esemény). **Külön issue javasolt**; hogy ez a #201 **merge-előfeltétele** vagy **külön implementációs lépés**, tulajdonosi döntés.
2. A #201 merge-e HOLD, amíg a tulajdonosi döntés és a független review nincs meg.
3. A proof PR-ek (#202–#210) és ágaik lezárása és törlése az evidence rögzítése után, a tulajdonos szavára.
4. A PR-07 (FULL/DIFF) a referencia védelme után folytatható; a workflow-eredet védelmének időzítése a fenti döntéstől függ.
