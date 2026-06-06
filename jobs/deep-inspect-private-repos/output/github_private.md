# github_private (CIC-basic-knowledge) — Részletes Feltárás

**Dátum:** 2026-06-06
**Lokális elérési út:** `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/source/CentralInfraCore/CIC-basic-knowledge`
**Remote URL:** `git@github.com:CentralInfraCore/github_private.git`
**Aktív branch:** `devel` (párhuzamosan: `d/feauture-quorumrelease`)
**Repo jellege:** Nem kód — deklaratív szemantikai gráf (NDJSON + Markdown + YAML)

---

## Mi ez a repo?

A `github_private` (belső nevén `CIC-basic-knowledge`) a **CIC ökoszisztéma AI-natív fogalmi tudásbázisa**. Nem hagyományos dokumentáció — deklaratív NDJSON gráfstruktúra YAML meta-annotációkkal. Ez táplálja a `cic-graph` MCP szerver KB-ját.

Jellemzői:
- Kétnyelvű (en/hu) fogalmi rétegek
- Gráf-alapú tartalom: node-ok = fogalmak, élek = relációk
- Nincs futtatható kód (nem buildelhető, nem tesztelhető Go/Python értelemben)
- Minden `.md` fájlhoz tartozik `.yaml` companion (metadata, tags, kategória, status)

---

## Könyvtárstruktúra (3 szint)

```
CIC-basic-knowledge/
  _graph.ndjson              — gyökér szintű gráf (fő NDJSON aggregátum)
  graph.ndjson.yaml          — gráf fájl companion YAML
  _ai_prompt_index.yaml      — AI prompt navigációs index
  _ai_prompt_index.explained.yaml — magyarázott AI index
  _ai_prompt_index.explained.md
  CONTRIBUTING.md
  CONTRIBUTING.yaml
  docs/
    en/                      — angol dokumentáció
      index.md + index.yaml
      README.md + README.yaml
      concept/               — CIC fogalmi alap
      reality/               — infrastruktúra valóság (relay, state, schema)
      interaction/           — szerepkör-specifikus bevezető (DevOps, PM, Architect)
      usage/                 — lifecycle, rollback, schema evolution
      meta/                  — relay modul szintű meta-adatok
    hu/                      — magyar dokumentáció (mirror struktúra)
      _graph.ndjson          — hu-specifikus gráf aggregátum
      index.md + index.yaml
      README.md + README.yaml
      concept/
      reality/
      interaction/
      meta/
      prompt/                — AI promptok (hu-specifikus)
      usage/
  meta/
    cic.md                   — CIC modul szintű meta-adat
    cic.yaml
    _graph.ndjson            — meta gráf
  profile/
    _graph.ndjson            — gráf profil node-ok
    README.md + README.yaml
  README.md                  — angol README (CentralInfraCore leírás)
  README.yaml
  README.hu.md               — magyar README
  README.hu.yaml
  README.ai.md               — AI-specifikus README
  README.ai.yaml
  LICENSE.md                 — CC BY-NC-SA 4.0
  LICENSE.yaml
  md.schema.yaml             — Markdown fájl séma
  .gitignore
```

---

## NDJSON Gráf Formátum

Minden `_graph.ndjson` fájl JSON Lines formátumú. Egy-egy sor egy gráf elem:

```json
{"id": "file_readme_md", "type": "file", "data": {"file_name": "README.md", "file_path": "README.md"}}
{"id": "para_readme_md_0", "type": "paragraph", "data": {"text": "# CentralInfraCore"}}
{"id": "edge_readme_md_p0", "type": "content_relation", "source": "file_readme_md", "target": "para_readme_md_0", "data": {"relationship_type": "contains"}}
```

**Node típusok (azonosított):**
- `file` — dokumentum node
- `paragraph` — szöveg bekezdés
- `concept` — fogalom node
- `reality` — infrastruktúra valóság elem
- `interaction` — interakció (szerepkör-specifikus)
- `usage` — használati eset
- `meta` — meta-adat node

**Él típusok:**
- `content_relation` (relationship_type: `contains`) — szülő-gyerek tartalom kapcsolat
- Egyéb éltípusok a `kb_data/edge_types.md`-ben dokumentálva

---

## YAML Companion Fájlok

Minden `.md` mellé `.yaml` fájl tartozik a metadata réteghez. Struktúra (md.schema.yaml alapján):

```yaml
tags:         [lista]
category:     "concept|reality|interaction|usage|meta|prompt"
used_in:      [lista — más dokumentumok vagy rendszerek]
status:       "implemented|scaffold|concept"
lang:         "en|hu"
```

Ezek a mezők a `make_source.py` feldolgozásakor chunk metadata-vá válnak, ami lehetővé teszi a `search_query` rule-bonus mechanizmusát és a `find_nodes` szűrőit.

---

## Tartalmi Rétegek

### `docs/en/concept/` és `docs/hu/concept/`
Az elméleti alap: mi a CIC, mik az axiómák, hogyan gondolkodik a rendszer.

### `docs/en/reality/` és `docs/hu/reality/`
Infrastruktúra-valóság: relay mechanizmus, állapotkezelés, schema réteg, ProofTrace.

### `docs/en/interaction/` és `docs/hu/interaction/`
Szerepkör-specifikus belépési pontok: DevOps, PM, Architect perspektívák.

### `docs/en/usage/` és `docs/hu/usage/`
Lifecycle példák, rollback, schema evolúció, konkrét használati esetek.

### `docs/hu/prompt/`
AI-specifikus prompt anyagok (hu). Magyar nyelvű, mert a fejlesztési komunikáció elsősorban magyar.

### `meta/`
CIC relay-modul szintű meta-adatok (nem az egész rendszer meta-ja, hanem a relay modul-szintű azonosítók).

### `profile/`
Gráf profil — valószínűleg a KB navigációs profil (AI számára: milyen célokra milyen node-okhoz kell navigálni).

---

## AI-Prompt Index

A `_ai_prompt_index.yaml` és `_ai_prompt_index.explained.yaml` az AI asszisztens számára navigációs térképet ad:
- Milyen típusú kérdéshez melyik dokumentum a belépési pont
- Fogalmi mélység szerinti csoportosítás
- Szerepkör-alapú navigáció

---

## Git Branch-ek

- `devel` — aktív fejlesztés (utolsó commit: `docs: trim and restructure reality/interaction docs`)
- `d/feauture-quorumrelease` — quorum release feature branch (fogalmi szint: concept státusz a ROADMAP szerint)

**Legutóbbi commit-ok:**
- `docs: trim and restructure reality/interaction docs`
- `docs: relay trust branch isolation — dev/prod CA tree separation`
- `docs: add auditor validation procedure and conversation-driven system meta`
- `feat: add missing companion YAML metadata for 7 MD files`
- `meta valuta concept` — új fogalom bevezetés

---

## CIC Kapcsolódások

- **cic-mcp-private**: ez a repo az MCP szerver fő KB forrása. A `make_source.py` feldolgozza a NDJSON gráfot és a Markdown/YAML fájlokat. A `kb_data/pkl/` tartalom ebből épül.
- **CIC-Relay**: a Relay architektúra (ProofTrace, cabinet, nexus) fogalmait ez a repo dokumentálja — elsősorban `docs/*/reality/` alatt.
- **cic-primitives**: a 7 primitív atom (Shape, Role, Behavior, Contract, Address, Identity, Event) fogalmi leírása valószínűleg itt él — vagy a `concept/` szekció alatt.
- **OpenIntentSign (.github)**: az OIS filozofiai alap közvetetten kapcsolódik — a bizalmi modell fogalmi gyökere, de külön repo.

---

## Státusz

**Aktív fejlesztés** — folyamatosan bővül a fogalmi dokumentáció. A `devel` branch aktív sprint-en van. A tartalom mennyisége és mélysége növekszik (legutóbb: trust branch isolation dok, auditor validation, companion YAML-ok tömeges feltöltése). A `d/feauture-quorumrelease` branch egy concept-szintű feature-t fejleszt (quorum döntési réteg, amely még nem rendelkezik runtime implementációval).

---

## Megjegyzések

1. Ez a repo a teljes CIC ökoszisztéma **episztemológiai alapja** — a fogalmak itt kapnak kanonikus definíciót, és az MCP szerveren keresztül minden AI session-ből elérhetők.

2. A kétnyelvűség (en/hu) szándékos: a fogalmi mélység és a promptok magyar nyelvűek, az architektúra dokumentáció mindkét nyelven létezik.

3. A `status` companion mező (implemented/scaffold/concept) itt is megjelenik — pontosan a CLAUDE.md háromszintű státusz rendszerének megfelelően.
