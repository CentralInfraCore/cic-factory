# AI-szintű optimalizálási terv

Felülvizsgált AI párbeszéd dokumentációja (orchestrátor session, 2026-06-11, 3. rész).
Előzmények: `docs/dev-environment-assessment.md` (1. rész),
`docs/kb-synthesis.md` (2. rész).

Cél: a drága, átfogó-kép modell (Fable/Opus) ritka session-jei mellett a
napi munka olcsó modellekkel fusson — hatékonyság-vesztés nélkül.
Minden javaslat tényekre épül (file:line evidenciával).

---

## Működési modell: két session-osztály

| Osztály | Modell | Mire | Kimeneti kötelezettség |
|---|---|---|---|
| **Átfogó kép** (ritka) | Fable/Opus | boot + architektúra-audit, kritikus spec-írás, rendszer-szintű review | session nem zárulhat perzistált artifact nélkül (`docs/` + memory) — a tudás így öröklődik át az olcsó session-öknek |
| **Végrehajtás** (gyakori) | Sonnet/Haiku | domain/repo jobok, mechanikus munka | output/ + claim-evidence tábla (K8) |

Az elv a KB saját axiómájának alkalmazása a fejlesztésre: a drága session
"örökséget" hagy (dokumentum, memory, focus pack), az olcsó session ebből
az örökségből dolgozik — nem újra-felfedez.

---

## Javaslatok prioritás szerint

### P1 — Modell-rétegzés ténylegesen bekötve (azonnali, legnagyobb megtakarítás)

**Tény:** a `meta.yaml` `agent.model` mezője **halott konfiguráció**:
- `tools/run-job.sh:106` — `claude --print` hívás `--model` flag nélkül
- `agents/agent-01/settings.json` — nincs `model` mező
→ minden agent-job a default (drága) modellen fut, a szándékolt rétegzés sehol
nem érvényesül.

**Teendő:**
1. `run-job.sh`: `agent.model` kiolvasása a meta.yaml-ból → `--model "$MODEL"`
2. `agent-01/settings.json`: default model = sonnet (semmi ne fusson véletlenül drágán)
3. `validate-spec.sh` új K-check: `agent.model` nem lehet üres — gépi kényszer,
   nem Claude-döntés

### P2 — kb_focus → prompt-injektálás (az olcsó modell hatékonyságának kulcsa)

**Tény:** a `meta.yaml` `kb_focus` mezőjét a `run-job.sh` nem használja —
az agent maga keres a KB-ban, ami gyenge modellnél gyenge felfedezést jelent.

**Teendő:** `run-job.sh` a prompt összeállításakor (78. sor környéke) a
`kb_focus` node-id-kból kötelező első olvasási listát injektál a promptba
(vagy a `focus_pack` MCP-tool eredményét). A gyenge modell felfedezésben
gyenge, végrehajtásban jó — ha a kontextust tálcán kapja.

### P3 — Költség-guard és költség-láthatóság

**Tény:** `run-job.sh:106` — nincs `--max-turns`, nincs timeout; egy elszálló
agent korlátlanul éghet. Az index.yaml-ban van duration (started/completed),
de token-költség nem látszik.

**Teendő:**
1. `--max-turns` limit (job-szinttől függően, pl. domain: 40)
2. `--output-format json` → usage mező kinyerése → `jobs/index.yaml`-ba
   költség-jel — így látható, melyik job-típus mennyibe kerül, és a
   modell-rétegzés hatása mérhető

### P4 — KB chunk-minőség (e session közvetlen tapasztalata)

**Tény:** a `make_source.py` section-szintű chunkolása fejléc-only chunkokat
termel (pl. c2205 = 6 sor cím, c2878 = 5 sor cím) — egy fogalom összerakása
sok get_chunk round-tripet igényel; emiatt csúszott ez a session is
fájlolvasásba. Továbbá a node `related_nodes` mezője path-alapú, nem node-id —
nehezíti a gráf-hopolást.

**Teendő (cic-mcp-private repo):**
1. minimum chunk-méret vagy fejléc+törzs összevonás az indexelőben
2. `related_nodes` → node-id feloldás indexeléskor
3. opcionális: `get_doc(file_path)` MCP tool — teljes dokumentum egy hívásból,
   a gráf-lokalizálás után (a hibrid recept MCP-oldali fele)

### P5 — ChatGPT formális csatorna

**Tény (2026-06-11 pontosítás):** a ChatGPT oldalon létezik a **CIC Explorer
HU v0.9.7 devel** custom GPT, az MCP-adatokkal feltöltött osztott kontextussal
— KB-megalapozott concept-rétegbeli partner, nem KB-vak külső eszköz.

**Teendő:**
1. `theads/` könyvtár a workdir-ben + sablon (kontextus, kérdés, AI-válasz,
   emberi döntés, rejected részek). ChatGPT/Gemini outputok kizárólag ide vagy
   job `ref/`-be kerülnek — a thead fejlécében a **GPT snapshot-verzióval**
   (pl. `source: CIC Explorer HU v0.9.7-devel`).
2. **Snapshot-frissítési fegyelem**: KB-release → GPT knowledge frissítés.
   Érdemes a cic-mcp-private indexelőbe egy "GPT export" targetet tenni
   (ugyanabból a forrásból, mint a pkl-ek) — így a két AI ugyanazt a kanonikus
   KB-t látja, csak más frissességgel.
3. Státusz-szabály változatlan: a GPT állapot-állításai a snapshot idejére
   érvényesek; implemented/scaffold státuszt csak az élő oldal (cic-graph MCP
   + kód) igazolhat.

### P6 — Review olcsóbbítása géppel

**Tény:** a `validate-spec.sh` (K1–K9) a spec oldalt már gépi kényszerrel fedi;
az output oldalt nem.

**Teendő:** `validate-output.sh` — merge előtt gépi ellenőrzés: kötelező
output-fájlok léteznek, claim-evidence tábla jelen van, file:line hivatkozások
feloldhatók. A drága (emberi/erős modell) review csak a tartalomra menjen,
ne a formára.

---

## Sorrend és függés

```
P1 (1 sor + 1 config)  →  azonnal, minden további futás olcsóbb
P3 (guard + mérés)     →  P1 hatása mérhetővé válik
P2 (focus injektálás)  →  olcsó modell minőségét védi
P6 (output-validátor)  →  review-költséget csökkenti
P4 (KB indexelő)       →  külön repo (cic-mcp-private), külön job
P5 (theads sablon)     →  bármikor, független
```

P1+P2+P3 együtt: a domain jobok futási költsége becsülhetően töredékére esik
úgy, hogy a spec- és review-kapuk (a minőség őrei) érintetlenek maradnak.
