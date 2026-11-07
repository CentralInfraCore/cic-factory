# 01a — a célzott folytatás hatókörének javaslata (ELŐKÉSZÍTÉS; a `--resume` HOLD, nem futott)

Állapot: 2026-11-07. Ez a dokumentum nem indít semmit. A tulajdonos döntése kell hozzá.

## 1. Mit csinál a `--resume` valójában (tools/run-job.sh, olvasva, nem futtatva)

- Ugyanabban a Claude Code session-ben folytat (`claude --resume 8f0c166f-…`; a session jsonl megvan: `~/.claude-personal/agents/cic-module-wasm-claude/projects/…/8f0c166f-….jsonl`). A meta `session_id` ki van töltve.
- A prompt **rögzített, általános** (run-job.sh:~642-655): "nézd át a workspace-t és az eredeti input.md Definition of Done listáját, azonosítsd mi van kész és mi maradt, fejezd be a hátralévőt. Push csak a feature branchre. Main-re NEM." **Nem szűkíthető paraméterrel.**
- A kimenetet `output/agent-output-resume-<STAMP>.md`-be írja (nem az `agent-output.md`-be).
- A push-ot az **agent** végzi (nem a script): az input.md git-szabálya szerint a feature branchre. A tulajdonos jelenlegi döntése: nincs push. A generikus resume-prompt ezt nem tiltja.
- A munka eredeti hatóköre a DoD-ban 5 output; a resume-prompt szerint az agent "befejezi a hátralévőt", vagyis a DoD alapján akár **újra is mérhet**, ha nem találja meg a saját korábbi eredményeit. Ez a "ne ismételjünk mérést" feltétel fő kockázata.

## 2. Három megoldási lehetőség (döntés kell)

| | Mi | Előny | Kockázat |
|---|---|---|---|
| A | Egy rövid **hatókör-kiegészítés** a workspace `input.md`-jének végére (helyi, a feature branchen, pusholatlan) + a resume a futtatott `run-job.sh --resume`-mal | a lifecycle (státusz, költség, naplózás) érintetlen; a szűkítés az agent által olvasott helyen van | az input.md a futás közben módosul: a run-history-ban rögzíteni kell; a push-tilalmat az agent szabályával szemben kell felülírni |
| B | `claude --resume <id>` kézzel, saját prompttal, a run-job.sh megkerülésével | pontos prompt, push-tilalom kimondható | kimarad a lifecycle: státusz/költség/index nem frissül, `error` marad a metában |
| C | A két outputot az **orchestrátor** írja meg a már ellenőrzött anyagból | nincs új agent-költség | a delegálás sérül: az orchestrátor saját munkáját "kapuzza", elveszik a függetlenség; nem javasolt |

Javaslat: **A**, a lenti hatókör-szöveggel, és a push-kérdés külön, explicit tulajdonosi döntéssel.

## 3. A javasolt hatókör-szöveg (az input.md végére; magyarul, mert Factory prompt)

> ## Folytatás — hatókör (2026-11-07)
> Az előző futás a fiókhasználati limitbe ütközött. Kész és megtartandó: `output/baseline.md`, `output/contract-mapping.md`. **Ne mérd újra** ami ezekben mért; ne indíts Docker/Go/mutációs mérést.
> Hátra van **kizárólag**: `output/relay-requirements.md` és `output/claim-evidence.md`. Az `agent-output.md`-t a limit-üzenet töltötte ki; a folytatás a saját `agent-output-resume-*.md`-jét írja, benne a kötelező jelentés-kérdésekkel.
> Bemenet a már elvégzett munka mellé: `ref/orchestrator-review-partial.md` (az orchestrátor független újramérései és megfigyelései). Ezt **bemenetként kezeld, ne állításként a saját mérésedként**: a `claim-evidence.md` Bizonyíték oszlopában minden sornál külön jelöld a forrást: `agent-mért`, `orchestrátor-újramért`, `dokumentált`, `NOT MEASURED`, `NOT INDEPENDENTLY VERIFIED`.
> Nem reprodukált eredmény nem lehet `mért` státuszú: a `module` lefedettség (82,7% vs 82,9%), a top-level tesztszám (55 vs 26; manuális 7 vs 8), a mutáció (159/217), a govulncheck, a Q3/Q6/Q9 sorok.
> **Push: NEM.** Ez felülírja az input.md git-szabályának push-lépését. Commit a workspace-ben megengedett, push nem. A munka végén állj meg.
> Nincs production-kód, séma, CI vagy dependency módosítás. A `compartmentId` helyéről nem döntesz: tulajdonosi döntésre váró kérdésként szerepeljen.

## 4. A két hiányzó output pontos tartalma (a DoD-ból és a vizsgálatból)

**relay-requirements.md** — oszlopok: követelmény-azonosító, Relay-fájl, jelenlegi viselkedés, kívánt viselkedés, negatív teszt, elfogadási feltétel; minden elem Relay-forrásból (fájl:sor, Relay `55a899f`). **Két külön szakasz kötelező:**
1. *Relay-oldali módosítást igénylő:* (R1) az op-szókészlet eltérése: a Relay csak `process|get|init|notify`-t ad át (`core/cabinet/cicwasm.go:277,283,289,295`, `service.go:~229-243` default elutasít), a modul nyolc ABI-opot vár (`module/abi.go:~36-51`); (R2) a tartós state-binding (a `provider_id`/OCID tárolása) Relay-oldali megvalósítása, nincs ilyen kód a `55a899f`-en; (R3) a Forms production bekötése: sem a Relayben, sem a modulban nincs Forms-hivatkozás (`*.go`, `go.mod`).
2. *A modulban javítható (nem Relay):* (M1) az `executionStep`/execution result nem ad vissza `resource_id`-t, miközben `docs/design/specs/provider-abi.md:99` előírja; (M2) a `compartment_id` hiánya az `execBinding`-ból a design-doksi (`provider-abi.md:73`) ellenére: **javasolt, nem elfogadott** irány, tulajdonosi jóváhagyásig; (M3) az `Observe` production útja nem használja a `normalizeObserved` védelmét: kötelező 01b blokkoló teszt (hiányzó `ipv6CidrBlocks` → nem lehet belőle levezetett `isIpv6Enabled=false`; a teszt a production `Observe`-ot hajtsa meg).
Minden követelménynél: státusz (`implemented|scaffold|concept`) a háromszintű definíció szerint.

**claim-evidence.md** — fejléc pontosan: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`. Egy sor minden állításhoz a baseline.md-ből és a contract-mapping.md-ből; a Bizonyíték fájl:sor/commit/parancs/kimenet-idézet; a KB-ból vett állítás `Forrás: KB c#### (file_path)` jelöléssel. Az 5 pontos reachability artifact (file:line hívási pont) is kerüljön be: `Observe provider.go:827→860→861`, `normalizeObserved` production hívó 0, `Execute` create-út (`provider.go:972→1013→1092`), Relay `callGuest` négy hívása.

## 5. A folytatás utáni lépések (a három feltétel szerint)
1. A workspace és a részleges eredmények megőrzése: a resume a meglévő workspace-ben fut; előtte `git -C <workspace> status` és a két kész output SHA-256-ja rögzítve; a futás után ugyanezek összevetve (a kész fájlok ne módosuljanak).
2. `tools/validate-output.sh` az előírt életciklus-helyen: az outputokat a lifecycle szerint a feature branchről kell a validátorhoz juttatni; mivel a push nincs engedélyezve, a validátor helyi futtatása előtt a tulajdonos dönt arról, hogy a feature branch pusholható-e (a script a `jobs/<id>/output/` helyet olvassa).
3. Orchestrátori review (három külön eredménycsoport), automatikus merge nélkül; a #35 merge-e külön döntés.

## 6. Döntéspontok a tulajdonosnak
1. Megoldás: A / B / C.
2. Push: marad a "nincs push" (akkor a `validate-output.sh` az élő mappán nem fut érdemben; helyi másolattal és annak jelölésével kell futtatni), vagy a feature branch (NEM main) push-a engedélyezett a validálás és a review miatt.
3. A hatókör-szöveg (3. szakasz) jóváhagyása vagy módosítása.
