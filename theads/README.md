# theads — felülvizsgált AI párbeszédek

Külső AI-eszközökből (ChatGPT / CIC Explorer GPT, Gemini, Codex) származó anyagok
**kizárólag** ide vagy egy job `ref/` könyvtárába kerülnek — soha nem közvetlenül
`docs/`-ba vagy job outputba.

## Miért

A CIC-ben a felülvizsgált AI párbeszéd maga is artifact (lásd `CIC-Relay/theads/`,
`CIC/teads/relay-trust-todo.md`). De egy külső eszköz állítása **nem** ugyanaz a
bizonyíték-osztály, mint az élő KB + kód:

- A CIC Explorer GPT ugyanazokat a pkl állományokat tölti be, mint a `cic-graph` MCP —
  tehát nem KB-vak. A korlát a **snapshot-drift** (feltöltéskori állapot vs. élő pkl)
  és az élő verifikáció hiánya.
- Ezért: a GPT állításai a **snapshot idejére** érvényesek. `implemented` / `scaffold`
  státuszt csak az élő oldal igazolhat (cic-graph MCP + forráskód).

## Sablon

Új thread: `theads/<téma>-<YYYYMMDD>.md`, ezzel a fejléccel:

```markdown
# <téma>

- source: CIC Explorer HU v0.9.7-devel   # vagy: ChatGPT / Gemini / Codex + verzió
- snapshot: <a KB-snapshot dátuma vagy verziója>
- dátum: <ISO 8601>
- kapcsolódó job: <job-id vagy ->

## Kontextus

Mit kérdeztünk és miért.

## Kérdés

Szó szerint.

## AI válasz

Szó szerint vagy tömörítve — jelöld melyik.

## Emberi döntés

Mit fogadtunk el, mit nem.

## rejected

Amit elvetettünk, és miért. **Ezt ne tervezd újra egy későbbi sessionben.**

## Verifikálandó

Azok az állítások, amiket az élő oldalon (cic-graph MCP / forráskód / CI) még
ellenőrizni kell, mielőtt tényként hivatkozunk rájuk.
```

## Szabály

A `rejected` szakasz kötelező, ha bármit elvetettünk. A `CLAUDE.md` „Felülvizsgált AI
párbeszédek" táblája ezekre a döntésekre hivatkozik — a `rejected` részeket egy későbbi
session nem tervezheti újra.
