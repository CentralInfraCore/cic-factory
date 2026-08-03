# Boot sequence — orchestrátor kötelező lépései

**Minden session elején és minden architektúrális job létrehozása előtt.**
Ezt NEM delegálod agentnek — te futtatod le.

## Kötelező lépések

### 0. Delta — mi változott a legutóbbi session óta

**Ezt futtasd először.** Fontosabb, mint bármelyik alábbi lépés: a „mi volt igaz
48 napja" sokkal kevesebbet ér, mint a „mi változott azóta".

```bash
git -C . log --oneline -15
git -C . status --short
tail -20 jobs/index.yaml          # totals: + a legutóbbi jobok állapota
gh pr list --state open           # nyitott review-k
```

Ez adja meg, hol tartunk. A `jobs/index.yaml` **auto-generált** (`tools/update-index.sh`) —
ez a job-állapot kanonikus forrása. Ne memóriából idézd fel, melyik job készült el.

### 0/b. Memória: index most, fájl később

Olvasd el a `MEMORY.md` indexet — **de ne olvasd el az összes memóriafájlt előre.**
Egy memóriafájlt akkor nyiss meg, amikor a feladat kijelöli, hogy releváns.

A memóriák dátumozottak és elavulhatnak; a repó és a KB az élő forrás. Ha egy
memória fájlt, függvényt vagy flaget nevez meg, ellenőrizd hogy még létezik-e,
mielőtt tényként hivatkozol rá.

### 1. KB státusz
`kb_status` — elérhető és friss?

### 2. Kanonikus invariánsok

`search_nodes` → `axioms`, `symbols`, `contract`, `limits` — **egyenként.**

A `search_nodes` több szavas lekérdezésre üres listát ad (mérve 2026-08-03:
`"axioms symbols contract limits"` → `[]`, `"axioms"` → 2 találat). Ha egy
lekérdezésbe fűzöd őket, üres kézzel jössz ki, és azt hiheted, nincs a KB-ban.

### 3. Relay fundamentumok — kötelező horgonyok

**A chunk-id NEM stabil azonosító. A file path az.**

A KB újraindexelésekor a chunk-id-k eltolódnak. 2026-08-02-én ez meg is történt
(2875 → 10590 chunk), és a korábbi négy horgony-id — `c781`, `c912`, `c927`,
`c365` — azóta **teljesen más tartalmat ad** (Go teszt-függvényeket és egy WASM
méret-konstanst). Ez rosszabb, mint ha nem létezne: a boot némán lefutottnak
látszik, rossz anyaggal.

Ezért a horgonyt **tartalom + file path** azonosítja, és a chunk-id csak
kényelmi gyorsítás, ami önellenőrző:

| Amit el kell olvasnod | File path (stabil) | chunk-id 2026-08-03-án |
|---|---|---|
| relay pozicionálás — végrehajtó motor, nem dönt, `NextHops` | `CIC-Relay/docs/hu/concept/relay_pozicionalas.md` | `c1719` |
| gráf-alapú végrehajtás — determinált, `ExecutionGraph` + séma + állapot | `CIC-Relay/docs/hu/concept/graf_vegrehajtas.md` | `c1677` |
| séma belső viselkedés — `StateRequirement`/`Dependencies`/`PluginRef`/`NextHops` | `CIC-Relay/docs/hu/concept/schema_kezeles.md` | `c1734` |
| `core/cabinet/` — schema/module/workflow registry + WASM | `CIC-basic-knowledge/docs/hu/repos/cic-relay.md` | `c4147` |

**Eljárás:**

1. Próbáld a chunk-id-t: `get_chunk("c1719")` stb.
2. **Ellenőrizd a visszakapott `file_path`-t** a fenti táblázat ellen. Ha nem
   egyezik, az id elavult — ne dolgozz vele.
3. Elavulás esetén keresd meg tartalom alapján:
   `search_query("relay executes declared operational graph, does not decide")`
   — a találat `file_paths` mezője azonosítja, hogy jó helyen jársz.
4. **Ha új id-ket találtál, írd be ide őket** a régiek helyére, és a memóriába is
   (`project_mcp_connect_fix`). A következő session ne fizesse ki újra.

Ez a négy horgony együtt ~20 sor. Szándékosan ennyi: nem áttekintés, hanem
**horgony** egy konkrét múltbeli tévút ellen (lásd lentebb).

Ha egy jövőbeli session azt találja, hogy ez a négy már nem a legjobb horgony
erre a célra, az a szabály felülvizsgálata — nem a kihagyása. A költség/haszon
arányt is figyelni kell, nem csak végrehajtani.

### 4. Amit ebből tudni kell mielőtt jobot írsz

```
séma → workflow (séma tudja melyik workflow tartozik hozzá)
workflow → modul (workflow mondja meg melyik modulokat kell hívni)
modul → get/set/notify (modul hajt végre)

A relay:
  - végrehajtja a deklarált műveleti gráfot (nem dönt, nem shortcutol)
  - StateRequirement/Dependencies/PluginRef/NextHops alapján halad
  - stateless — a séma és a workflow a "beavatkozás helye", nem a relay kódja
```

## Miért kötelező

Ha nem futtatod le: architektúrális állításokat teszel anélkül hogy tudnád
mi van a KB-ban. Ez a Terraform-centrikus tévút forrása volt — a Cabinet
séma→workflow→modul összerendelési modelljét nem olvastuk el, és egy külső
eszközre épülő post-apply observer modellt gyártottunk helyette.

## Jel hogy kihagytad

- Terraformot vagy más külső eszközt teszel a relay elé orchestrátorként
- "A relay megfigyeli amit X csinál" — relay nem observer, hanem executor
- Job spec-et írsz relay architektúráról anélkül hogy a 3. pont négy horgonyát elolvastad
- `get_chunk` visszaad valamit, és te **nem nézted meg a `file_path`-ját** — akkor
  nem tudod, hogy a horgonyt olvastad-e vagy valami mást
