# relay-ci-parity-06l-bootstrap-workflow — a 4.6a bootstrap workflow-fájl (CIC_Relay #212, 9. lépés)

## Kontextus

A #83 (0. fázis tulajdonosi forgatókönyv) mergelve (505e639). A 4.6a pont szerint a G0 (4.8 3., 9., 10. sor) egyetlen, külön jóváhagyott bootstrap workflow-fájlt igényel az X repón (`ci-adversarial-lab`), amelynek egyetlen jobja a `CHECK_NAME`. Tulajdonosi GO (2026-11-22): a bootstrap workflow elkészítése külön PR-ban, aláírt committal és tartalmi review-val; a tulajdonos párhuzamosan megkezdi az A sor 4.1–4.5 lépéseit.

## Hatókör

**Kizárólag a fájl, az ellenőrzője és a használati leírás.** Nem pusholok az X repóra (nem is létezik még általam látott módon), nem hozok létre semmit a mérési környezetben, nem futtatok mérést. A fájlt a tulajdonos pusholja (K-8).

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06k-phase0-owner-runbook/output/phase0-owner-runbook.md` (4.6a kötött tartalma, 4.7, 4.8 3., 9., 10. sor)
- `jobs/relay-ci-parity-06j-execution-decision-package/output/execution-decision-package.md` (K-8, 4.0 szerepek)

## Elfogadhatatlan rövidítések

- NEM fogadható el: a 4.6a kötött tartalmától eltérő fájl (secrets, environment, harmadik fél akciója, írási jog, más trigger, több job); a fájl ellenőrzője legyen olyan, amely tud bukni (planted eltérések).
- NEM fogadható el: a fájl létezése vagy a helyi ellenőrzés = a GitHubon működik; a futási viselkedés dokumentált, nem mért, amíg a tulajdonos nem futtatta.
- NEM fogadható el: a 4.6b mérési csomag, kanári-olvasó vagy bármilyen mérési logika a bootstrapben.
- NEM fogadható el: írási művelet a mérési környezeten vagy az éles szervezeten; hitelesítő adat átadása nekem.

## Output

- `output/bootstrap-workflow.md` — használati leírás, kötött tartalom, tulajdonosi push-lépések (olvasó ellenőrzéssel), claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)
- `output/payload/lab-gate.yml` — a bootstrap fájl (az X repóba `.github/workflows/lab-gate.yml` útvonalra kerül)
- `output/check-bootstrap-workflow.py` — fail-closed ellenőrző önteszttel

## Git

Feature branch `feature/relay-ci-parity-06l-bootstrap-workflow`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
