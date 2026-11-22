# relay-ci-parity-06k-phase0-owner-runbook — a 0. fázis tulajdonosi előkészítési forgatókönyve (CIC_Relay #212, 8. lépés)

## Kontextus

A #82 (végrehajtási döntési csomag) mergelve (7cf5dab). A K-1–K-8 ajánlásokat a tulajdonos elfogadásra javasolta (K-7: MEASURE), a szervezet neve `CIC-Security-Lab`, a két repó `ci-adversarial-lab` (X) és `ci-identity-lab` (Y). Tulajdonosi GO (2026-11-22): a 0. fázis tulajdonosi előkészítéséhez szükséges **konkrét, sorrendbe rendezett parancsok és beállítások** elkészítése; az O-2a, O-3 és O-5b előkészítése párhuzamos sávként tervezett. A tényleges mérések, kulcsműveletek és éles konfigurációmódosítások HOLD.

## Hatókör

**Kizárólag forgatókönyv (dokumentum).** Nem hajtok végre semmit a mérési környezeten: nincs szervezet-, repó-, fiók- vagy App-létrehozás, nincs beállítás-módosítás, nincs kulcsművelet, nincs mérés. A forgatókönyv parancsait és beállításait a tulajdonos futtatja. Az egyetlen környezeti tevékenységem csak olvasó metaadat-lekérdezés (név szabad-e, a Relay Actions-beállításai); az eredmény „olvasott" jelöléssel szerepel.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06j-execution-decision-package/output/execution-decision-package.md` (4.0 E-1…E-6 és szerepek, K-1…K-8, O-2…O-5, 5.1 kapuk)
- `jobs/relay-ci-parity-06i-exploratory-measurement-plan/output/exploratory-measurement-plan.md` (2.5 környezet és kanári, 3. szakasz tételei)

## Elfogadhatatlan rövidítések

- NEM fogadható el: parancs vagy beállítás, amelynek a hatása nincs leírva és nincs olvasó ellenőrzése; a forgatókönyv megléte ≠ működik.
- NEM fogadható el: a dokumentált (de ebben a sessionben nem ellenőrzött) platformviselkedés mértként jelölése; a forgatókönyv elfogadása ≠ sikeres végrehajtás.
- NEM fogadható el: hitelesítő adat, kulcs vagy token (valódi App-kulcs, gépi fiók jelszava, személyes token) átadása nekem; a forgatókönyv a kulcs nem hozzám kerülésére épül.
- NEM fogadható el: bármilyen írási művelet a mérési környezeten vagy a Relay-n a tulajdonos futtatása nélkül; mérés, kulcsgenerálás, App-kulcs létrehozása a 0. fázisban.
- NEM fogadható el: a K-1–K-8 ajánlások módosítása vagy újabb tervezési kör nyitása; eltérés csak megjelölt, indokolt pontosítás lehet.

## Output

- `output/phase0-owner-runbook.md` — a G0 kapu lépései sorrendben (parancs, hatás, olvasó ellenőrzés, a nekem visszaadandó nem titkos kimenet, visszafordítás), a párhuzamos sáv (O-2a, O-3, O-5b, Y repó) előkészítési terve, K-4 olvasott értékei, leállási feltételek; claim-evidence tábla, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch `feature/relay-ci-parity-06k-phase0-owner-runbook`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
