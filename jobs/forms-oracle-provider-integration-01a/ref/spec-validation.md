# Spec-validáció: jobs/forms-oracle-provider-integration-01a/input.md

Dátum: 2026-11-07. Futtatta: a workdir orchestrátor, a job indítása **nélkül**. A job státusza: `pending`.

## Gépi ellenőrzés

- `tools/validate-meta.sh forms-oracle-provider-integration-01a`: **OK**.
- `tools/validate-spec.sh forms-oracle-provider-integration-01a`: **GO** (exit 0). Egy figyelmeztetés: **K11** — a `kb_focus` üres. Szándékos: a chunk-id-k nem stabilak, és egyet sem sikerült tartalmilag (`get_chunk` `file_path`) igazolni; az input.md az agentnek írja elő, hogy maga keressen, és minden kiindulási pontnál rögzítse a forrását.

## Evidence-alapú ellenőrzés (`/job-validate` K1–K11)

| Kritérium | Státusz | Idézet a specből |
|---|---|---|
| K1 — Forrás | PASS | „Klónozd a workspace-be (csak olvasásra, **soha ne pushold őket**): `git clone git@github.com:CentralInfraCore/cic-module-oracle-cloud.git` (ág: `devel`) …"; „olvasd a `${CIC_RELAY_PATH}` alatti forrást" (19–23. sor); a fájllista a modulra, a Formsra, a primitívekre (25–31. sor) |
| K2 — Státusz def + módszer *(kézi)* | PASS | „**implemented** — production kódban hívódik **és** tesztek fedik. Bizonyítás: … `grep -rn \"<Szimbólum>\" --include=\"*.go\" | grep -v \"_test.go\"` … fájl:sor megadva; VAGY a `deadcode ./...` kimenete"; „**scaffold** — … feltételes elágazás mögött él (`if X == nil`, `if !Flag` …)" (33–34. sor) |
| K3 — Tiltott rövidítések | PASS | „❌ „a fájl létezik" ≠ implemented · ❌ „a teszt lefedettsége 8x%" ≠ implemented · ❌ „a README/spec/KB leírja" ≠ implemented" (41. sor) |
| K4 — Output formátum | PASS | „`output/baseline.md` … `output/contract-mapping.md` … `output/relay-requirements.md` … `output/claim-evidence.md` … `output/agent-output.md`" (Output szakasz) |
| K5 — Ellenőrizhetőség *(kézi)* | PASS | „Minden `implemented` szimbólum mellett production hívó **fájl:sor** vagy a `deadcode` kimenet — nem az agent állítása." (Ellenőrizhető elvárások, 1. pont) |
| K6 — Negatív példák *(kézi)* | PASS | „❌ Ne csinálj mockot vagy kézi adaptert egy hiányzó leképezés elfedésére; a hiányt rögzítsd coverage rekordként." (46. sor); „Nincs valós OCI hívás … **nem módosítasz kódot, sémát, CI-t vagy `docs/**`-t egyik repóban sem**" |
| K7 — Call-chain grep + _test.go kizárás | PASS | „`grep -rn \"<Szimbólum>\" --include=\"*.go\" | grep -v \"_test.go\"` — legalább egy production hívó, **fájl:sor megadva**" (33. sor) |
| K8 — Claim-evidence tábla | PASS | „`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`" (claim-evidence.md leírás) |
| K9 — Reachability artifact | PASS | „VAGY a `deadcode ./...` kimenete (a `module/` és a `tools/oci-extract` alatt) kerüljön az outputba" (A.1) és az „Ellenőrizhető elvárások" 1. pontja |
| K10 — agent.model kitöltve | PASS | meta.yaml `agent.model`: `claude-opus-5` |
| K11 — kb_focus kitöltve | WARN | meta.yaml `kb_focus: []` (indoklás fent; nem blokkoló) |

## Összesítés: GO (a job indítása külön döntés)

A spec teljesíti a gépi és az evidence-alapú kritériumokat; a K11 figyelmeztetés ismert és indokolt. A job **nem lett elindítva**; az orchestrátori review és a külön GO a job indításához hátravan. A Relay és az érintett repók változatlanok.

## A review-kör után bekerült pontosítás

Az orchestrátori review a leltár elemei közül a **verzió, commit-pin, licenc és függőségkezelés** együttesét kérte; az első változat a licencet és a commit-pint tartalmazta, a függőségkezelést (hogyan hivatkozhatja a modul a Forms kódot) és a TinyGo/WASM-fordíthatósági mérést nem. Ez bekerült a B szakaszba (57. sor körül), az újrafuttatott `validate-spec.sh` és `validate-meta.sh` eredménye változatlanul GO és OK.
