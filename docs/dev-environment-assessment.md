# Fejlesztési környezet értékelés — költséghatékonyság vs. hatékonyság

Felülvizsgált AI párbeszéd dokumentációja (orchestrátor session, 2026-06-11).
Cél: optimális fejlesztési környezet összerakása, amely költséghatékony anélkül,
hogy elveszítené a hatékonyságát — beleértve a ChatGPT szerepének tisztázását.

Forrás-session: boot sequence lefutott (kb_status friss, c781/c912/c927/c365 olvasva),
input: `docs/ecosystem-map.md`, `jobs/index.yaml`, agent-01 config, PoC állapot-memória.

---

## 1. Ökoszisztéma-pillanatkép (2026-06-11)

| Réteg | Komponensek | Státusz |
|---|---|---|
| **Runtime** | `CIC-Relay` (Go 1.25, wazero WASM, ProofTrace) | implemented — devel zöld, demo-ready (`/set` → modul → ProofTrace → `/v1/proof/verify`) |
| **Schema/Trust** | `CIC-Schemas` (compiler + Vault Transit signing), `cic-primitives` (7 atom) + 5 domain repo, `cic-oci` | Schemas+primitives implemented; `cic-oci` **concept** — séma-terv kész (v0.1.0), repo még nem létezik |
| **Tudás** | `cic-basic-knowledge` (NDJSON gráf) → `cic-mcp-private` (FAISS+BM25, 25 tool, stdio MCP) | implemented |
| **Munkavégzés** | `cic-factory`: git-követett job-ok, izolált agent-klónok, Vault-aláírt commitok, hook-védett agent | implemented — 21 done job, 6 pending |

**Adatfolyam:** KB → MCP → orchestrátor/agent → job spec → agent-klón →
feature branch → GitHub review → merge. Párhuzamosan: Schemas → Vault-aláírt
artifact → Cabinet → relay végrehajtás → ProofTrace.

**Aktuális front:** PoC domain sub-jobok. `poc-infra-01` done; pending:
`poc-observer-plugin-01`, `poc-drift-detection-01`, `poc-rollback-01`,
`poc-demo-script-01`, `poc-schema-signing-01`, `base-repo-explore-01`.

---

## 2. Alapelv

A rendszer legdrágább hibamódja bizonyítottan **nem a token-költség, hanem a
rossz irányú output** (Terraform-tévút, sub-job duplikáció — mindkettő napokban
mért review-költség). Ebből következik:

> **A kontextus-építésen spórolj, a kontroll-pontokon soha.**

---

## 3. Ami már jól optimalizál — megtartandó

- **cic-graph MCP a fő költségcsökkentő**: graph-first reasoning + `kb_focus`
  a meta.yaml-ban → az agent nem 15 repót scannel, hanem 5–10 chunkot olvas.
  Nagyságrendi token-megtakarítás job-onként.
- **`ecosystem-map.md` + job-output újrafelhasználás (`ref/`)**: egyszer
  fizetett feltérképezés, sokszor olvasva.
- **Boot sequence + review pipeline (output → spec → bridge)**: olcsó
  biztosítás drága hiba ellen. Itt spórolni hamis költséghatékonyság.

---

## 4. Legnagyobb kihasználatlan kar: modell-rétegzés job-szint szerint

A `meta.yaml` `agent.model` mezője tudatosan használandó:

| Job-szint | Jelleg | Modell |
|---|---|---|
| orchestrator / architektúra | spec-írás, bridge-review — a hiba lefelé sokszorozódik | erős (Opus/Fable) |
| repo | build, lint, audit, jól specifikált scope | Sonnet |
| domain, mechanikus | YAML-generálás kész terv alapján, fmt-fix típus | Sonnet vagy Haiku |

Tipikus rejtett költség: `relay-fmt-fix` típusú jobhoz erős modellt égetni.

**Rövid távú alkalmazás:** `poc-demo-script-01` és `base-repo-explore-01`
mehet kisebb modellel; `poc-observer-plugin-01` (ahol már volt MISALIGNED path)
maradjon erős modellen, szigorú `kb_focus`-szal.

---

## 5. ChatGPT szerepe — körülhatárolva

**Korrekció (2026-06-11):** a ChatGPT nem KB-vak — a felhasználó osztott
kontextusa fel van töltve az MCP adataival, és létezik a **CIC Explorer HU
v0.9.7 devel** custom GPT (KB-snapshot RAG-gal). A CIC-ről kapásból,
KB-terminológiával lehet vele beszélni.

**Amit a snapshot NEM ad** (itt marad a határ):
- **élő állapot**: a snapshot a feltöltéskori KB — a live KB és a repo-k
  azóta változhatnak (snapshot-drift),
- **háromszintű státusz-verifikáció**: implemented/scaffold/concept állítást
  kód ellen ellenőrizni nem tud — nála minden állapot-állítás a snapshot
  idejére igaz, jelen időre **concept**,
- repo-állapot, boot sequence, Vault-lánc, commit-jog.

**Ahol olcsó és jó (a snapshot miatt erősebb, mint korábban felmértük):**
- KB-megalapozott koncepcionális sparring, spec-vázlatok CIC-terminológiával,
- második vélemény spec-eken *mielőtt* job lesz belőlük,
- onboarding/magyarázat külső szereplőknek (a custom GPT erre kész eszköz),
- KB-független munka: doku-vázlatok, fordítás, generikus Go/Python/OCI kérdések.

**Forrásazonosság (2026-06-11 megerősítés):** a GPT knowledge ugyanazokat a
pkl állományokat tölti be, amelyeket a cic-graph MCP is olvas. A két AI-oldal
tehát **ugyanabból a kanonikus KB-ból** dolgozik — nincs olyan, amit a GPT
látna, de az MCP ne. Az egyetlen valódi különbség a **frissesség**: az MCP-oldal
élő (pkl mtime szerint), a GPT-oldal a feltöltéskor befagyott snapshot.

**Következmény:** nincs ok a GPT-be belépni adatért — amit ott kérdeznél, azt
az MCP-n élőben és kód ellen verifikálva kapod meg. A GPT értéke az
**elérhetőség** (külső szereplő, onboarding, ChatGPT-felület), nem külön tudás.

**Frissességi fegyelem:** KB-release → GPT knowledge újratöltés ugyanabból a
pkl-forrásból; a belőle származó anyagokon jelölni a snapshot-verziót.

**Beléptetési szabály:** a kimenete mindig a már létező csatornán jön be —
`theads/`-stílusú felülvizsgált párbeszédként vagy job `ref/` anyagként,
sosem közvetlen "igazságként". Bevált minta: thead01/thead02 rejected döntései
épp ilyen review-kból születtek.

**Amit ne kapjon:** bármi, ami repo-állapotot, KB-státuszt vagy commit-jogot
igényel — ott a hamis magabiztosság költsége nagyobb, mint a megtakarítás.

---

## 6. Összegzés

A környezet váza már költséghatékonyra van tervezve (KB-fókusz, izolált olcsó
agent-futások, újrafelhasznált térképek). Két hangolnivaló:

1. **modell-rétegzés job-szintenként** (`agent.model` tudatos kitöltése),
2. **ChatGPT formális beengedése a concept-rétegbe** a meglévő review-csatornán
   keresztül,

— a kontroll-pontok (boot sequence, review pipeline, Vault-lánc,
reachability-DoD) érintése nélkül.
