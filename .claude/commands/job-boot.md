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
`search_nodes` → `["axioms", "symbols", "contract", "limits"]`

### 3. Relay fundamentumok — kötelező chunk-ok
```
get_chunk("c781")  — Cabinet: schema→workflow→modul összerendelés
get_chunk("c912")  — relay pozicionálás: deklarált gráfot hajt végre, nem dönt
get_chunk("c927")  — séma belső viselkedés: StateRequirement/PluginRef/NextHops
get_chunk("c365")  — Cabinet interface: schema/module/workflow registry
```

Ez a négy chunk együtt ~20 sor egy 2875 node-os KB-ból. Szándékosan ennyi:
nem áttekintés, hanem **horgony** egy konkrét múltbeli tévút ellen (lásd lentebb).
A `c365` önmagában két sor — a `c781`+`c912`+`c927` hármas hordozza a tartalmat.

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
séma→workflow→modul összerendelési modelljét (c781) nem olvastuk el,
és egy külső eszközre épülő post-apply observer modellt gyártottunk helyette.

## Jel hogy kihagytad

- Terraformot vagy más külső eszközt teszel a relay elé orchestrátorként
- "A relay megfigyeli amit X csinál" — relay nem observer, hanem executor
- Job spec-et írsz relay architektúráról anélkül hogy c781/c912/c927 elolvastad
