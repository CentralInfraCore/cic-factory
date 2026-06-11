# KB-szintézis — mit hoz ki az AI a tudásanyagból

Felülvizsgált AI párbeszéd dokumentációja (orchestrátor session, 2026-06-11, 2. rész).
Előzmény: `docs/dev-environment-assessment.md` (1. rész — fejlesztési környezet értékelés).

Kérdés: a factory mellett mit tud a benne lévő tudásanyag — mit hoz ki belőle az AI?
Forrás: cic-graph MCP (kb_status, search_nodes, get_chunk, neighbors, guided_path,
search_query) + teljes dokumentum-olvasás a KB forrásrepóból.

---

## 1. Háromszintű gondolati architektúra

A KB nem dokumentumgyűjtemény, hanem konzisztens levezetési lánc:

| Réteg | Tartalom | Kulcsállítás | Státusz |
|---|---|---|---|
| **Morális/filozófiai** (CICtor, 9 axióma) | identitás öröklődik, nem kérvényezhető; licenc = identitás = felelősség; nincs központi CA; a döntés lassú, de visszavonhatatlan | "a rendszer morálisan skálázódik, nem topológiában" | **concept** |
| **Jogi/működési** (OIS: Obligation–Intent–State) | a szándék önmagában soha nem elég; minden State visszavezethető Intent+Obligation párra | "CIC = hogyan bizonyítunk, OIS = miért engedtük meg" | **részben hidalt** — ProofTrace implemented, Obligation-ellenőrzés concept |
| **Fizikai/bizonyítási** (reality/) | ProofTrace lánc ↔ PBS root-hash → state commit; drift taxonómia (chain: fork/replay/key-legitimacy; state: soft/reconciliable/hard) | "a drift nem hiba, hanem bizonyíthatósági feszültségjelző" | **épülő híd** — a pending PoC jobok pont ezt építik |

---

## 2. Önhasonló minta minden szinten

A korpusz egyetlen elvet variál végig:

> **Semmi nem érvényes kijelentés által, csak örökölt gyökérből való
> bizonyítható levezetés által.**

- identitás: öröklési útvonal (1. axióma)
- séma: slot contract (`sealed`/`defaulted`/`required`) — gépileg ellenőrzött öröklés a 7 atomból
- állapot: `CommitRef = SHA256(head + rootHash + ts)` — igazolt állapot-horgony, nem snapshot
- licenc: nem a műveletre, hanem a commit minőségére vonatkozik
- **factory**: Vault-aláírt commitok, force-push tiltó hookok, review-kényszer —
  a fejlesztési környezet maga a "lassú igazság" elv futó példánya

---

## 3. A drift-modell már átment a hídon

A reality réteg 3-kategóriás drift-diagnózisa (`NO_DRIFT`/`RECONCILIABLE_DRIFT`/
`HARD_DRIFT`, policy: automatikus → operátori → kötelezően emberi) lett a PoC
drift-modellje — a repo-plan 4-kategóriás változata helyett. A KB tehát nem holt
elmélet, hanem ténylegesen normatív tervezési forrás.

---

## 4. Feszültségpont: 6. axióma vs. implementált CA-lánc

A 6. axióma: *"Nincs szükség központi hitelesítő hatóságra — a CICtor modell
CA-alapú rendszerekkel inkompatibilis."* A mai implementált trust-lánc viszont
klasszikus CA-hierarchia (Root CA → Intermediate → CIC Source CA → developer cert,
Vault PKI scaffold).

A koncepcionális válasz létezik — **quorum rootca modell** (7/26 Shamir-szeletelés,
körkörös propagáció, belépési algoritmus) —, de teljesen concept státuszú.

**Bridge-megállapítás:** a modell létezik, az implementációs híd a quorum-alapú
trust-nél megszakad — a Vault CA-lánc pragmatikus interim. Javaslat: ezt tudatos,
dokumentált interim döntéssé tenni.

A gráf (search_query) ide köti a relay oldali `CIC-Relay/docs/en/concept/
certificate-validation.md`-t is — a feszültség mindkét oldala dokumentált.

---

## 5. Meta-szint: a ChatGPT-szerep eredete

A `conversation_driven_system.md` rögzíti: a CIC ChatGPT-vel (később Geminivel)
folytatott párbeszédből született — "az AI a formalizáló erő, a döntés mindig
emberi". A dev-environment-assessment.md-ben javasolt ChatGPT-szerep
(concept-réteg, review-csatornán beléptetve) tehát nem új ötlet, hanem a rendszer
eredeti működési módjának formalizálása. A tudásgráf a beszélgetések lenyomata —
md/YAML/Go vetületek egy közös ontológiai magra.

---

## 6. Módszertani tanulság — MCP-first (orchestrátor önkorrekció)

A szintézis első körében az AI a chunk-fejlécek után közvetlen fájlolvasásra
váltott. A felhasználó jelezte: a tudásanyag az MCP-ben van — azt kell használni.

**Mit ad a gráf, amit a fájlolvasás nem:**
- **élek**: `refers-to`/`related-to` súlyokkal és evidence-szel (pl. az axióma-node
  7 kapcsolata) — a fogalmi összefüggés nem következtetés, hanem adat
- **guided_path**: olvasási sorrend concept → architecture → flow → implementation
- **search_query** (FAISS, többnyelvű): repón átívelő találatok — pl. a CA-feszültség
  kereséskor a relay implementációs doksit is felszínre hozta, amit a fájl-bejárás kihagyott
- **kanonikus metaadat**: tags, category, used_in, related_nodes

**Rögzített recept (graph-first, hibrid):**
1. felfedezés, reláció, státusz: **mindig MCP** (`search_query`, `search_nodes`,
   `neighbors`, `guided_path`)
2. teljes dokumentum mélyolvasás: Read a gráf által azonosított fájlra —
   csak miután a gráf lokalizálta és kontextusba tette
