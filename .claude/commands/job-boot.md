# Boot sequence — orchestrátor kötelező lépései

**Minden session elején és minden architektúrális job létrehozása előtt.**
Ezt NEM delegálod agentnek — te futtatod le.

## Kötelező lépések

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
