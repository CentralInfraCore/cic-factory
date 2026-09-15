# Session-napló — a `standards/yang/` felülvizsgálata és az első javítások

Folytatás a `SESSION-2026-09-10-schema-registry-onboarding.md`-hez képest —
ugyanaz a szál, három nap kihagyással. A user a `network` domainre alapozott
PoC-ot vetette fel, ez vezetett a `standards/yang/` mélyreható átvizsgálásához,
ami egy külső review-t és abból induló, tényellenőrzött javítás-sorozatot hozott.

---

## Előzmény — network-alapú PoC felvetése, majd lassítás

A session azzal indult volna, hogy "kezdjünk el egy újabb nagy részt PoC
méghozzá a network alapján" — de mielőtt bármit terveztem volna, a boot
sequence-t kellett lefuttatni (a `CIC/CLAUDE.md` szabálya szerint
architekturális munka előtt kötelező). A négy relay-horgony (`c1719`,
`c1677`, `c1734`, `c4147`) még mindig a várt file-okra mutatott, nincs drift.

Egy `AskUserQuestion`-t a user elutasított ("hova rohansz") — jelezve, hogy a
strukturált, több-részes kérdés-özön korai volt egy hosszú, fárasztó
munkamenet után. Ez tanulság: a scope-tisztázás nem mindig kérdőív formájában
kell, néha elég hagyni, hogy a user a saját tempójában vezesse a beszélgetést.

## A `general/network/` és `standards/yang/` réteg feltérképezése

Sorban átnézve: `network-interface` (DomainComposition, 941 sor),
`switch-netconf-adapter`/`ovs-adapter` (AdapterContract), majd a 9
YANGBlock (`ietf-interfaces-{base,physical,logical,vlan,tunnel}`,
`ietf-ip-{v4,v6}`, `ietf-lldp`, `cic-yang-block-schema`), majd egy szinttel
mélyebben a `~/sync/git.partners/CentralInfraCore/primitives-group/cic-yang/release/`
alatti aláírt `PrimitiveRelease` bundle (22 spec: 9 YANGBlock + 13 kernel
primitíva — `Shape`/`Role`/`Contract` és társaik).

Menet közben több, korpusz-szintű ellenőrzéssel megerősített/cáfolt
megfigyelés (részletesen a beszélgetésben, összefoglalva a threadben):
egy dangling `interface_type` hivatkozás a `physical` blokkban, egy
`type in [logical, bridge]` érvénytelen enum-érték a `network-interface`-ben
(a "bridge" a YANG-rétegen valós, de a DomainComposition saját, leegyszerűsített
`type` enumjában nem létezik), és a `binding_surface.adapter: network-adapter`
— a `#27` (`compute-adapter`) pontos harmadik esete, amit a repó saját
README-je már korábban is jelzett, de sosem lett issue-vá.

**Fontos módszertani pont:** a `cic-yang` repó (a `standards/yang/` eredeti
forrása) **archivált**, `v0.1.3`-on fagyva — a `#19` VLAN-javítás (`v0.1.4`)
csak a `cic-schema-registry` másolatában él, sosem került vissza. A
`cic-primitives` viszont **aktív**, és van egy kiadott `primitives/@v0.2.0`
tagje, aminek a tartalma jelentősen túlnőtt azon, amit a `cic-yang` bundle
befagyasztott.

## Külső review + tényellenőrzés

A user egy külső AI-review-t hozott a `standards/yang/`-ról (P0/P1
súlyozással, 8 tételes lista + egy NAT-javaslat + sor/oldalszám-becslés a
teljes network vocabulary-ra). Mielőtt bármit elfogadtam volna belőle,
függetlenül ellenőriztem a legkeményebb állításokat:

- **`RFC 8516` tényleg nem LLDP** — `WebSearch`-csel megerősítve: CoAP
  "Too Many Requests" hibakód.
- **A `cic-primitives` `Role`-modell háromtengelyes felbontása NEM
  feltételezés** — lekérve az élő repót, `primitives/@v0.2.0` tag,
  `schemas/atomic/role.yaml` szó szerint ugyanazt mondja, mint a review,
  ugyanazzal a példával ("last seen peer" / LLDP-szomszéd).
- **`RFC 8512` valóban NAT/NPT YANG modul** — megerősítve.
- A dangling `interface_type` hivatkozást én magam is megtaláltam,
  függetlenül, a review megkapása előtt.

Saját hozzátett észrevétel, amit a review nem tárgyalt: a teljes `tools/`
grep-elve — **semmilyen kód nem olvassa** a `yang_refs`/`yang_composition`/
`applicable_when`/`required_when`/`contract` mezőket. A `standards/yang/`
réteg ma tisztán dokumentáció. Ezért a review 12 000 soros bővítési
javaslatát **nem fogadtam el jelenlegi lépésnek** — a meglévő ~950 sor sincs
gépileg kikényszerítve, egy tízszeres bővítés ezt csak súlyosbítaná.

## thead + issue-k + első javítás

A user kérésére, ebben a sorrendben:

1. **`theads/thead01.txt` + `thead01.meta.yaml`** a `cic-schema-registry`-ben
   — a nyers külső anyag megőrizve, plusz a tényellenőrzött review
   (accepted/rejected/státusz), a `CIC-Relay/theads/` mintáját követve.
   PR #41, mergelve `devel`-be.
2. **7 issue nyitva** a `cic-schema-registry`-ben: `#42` (LLDP RFC-hiba, P0),
   `#43` (Role-modell elavult a meta-sémában), `#44` (dangling
   `interface_type`), `#45` (`extends` override-szemantika hiánya), `#46`
   (RFC provenance több mezőn), `#47` (VLAN/switchport szétválasztás —
   tervezési javaslat), `#48` (NAT blokk — tervezési javaslat, explicit
   jelezve hogy a 12k-soros scope nincs elfogadva).
3. **Az első, legbiztosabban ellenőrzött javítás elkezdve**: `#42`
   (LLDP RFC-tévedés) — `metadata.source`/`yang_source`/`yang_module`
   javítva IEEE 802.1ABcu-2021-re, mind az 5 `origin: rfc8516` mező
   `ieee8021ab`-re, a meta-séma mindkét `origin` enumja (field-szintű és
   notification-szintű) is javítva. PR #49, `make check`/`pytest` zöld
   lokálisan.

## Amit nyitva hagytunk, tudatosan

`#43`–`#48` nincs elkezdve — mind nagyobb tervezési/scope-döntést igényel,
nem egysoros javítás. A `#25` (`KubernetesCluster` backend/provider) a
2026-09-10-i körből is nyitva maradt. A `network`-alapú PoC eredeti kérdése
(mi legyen a szubsztrátum, mi legyen a mai kimenet) még mindig nincs
eldöntve — ez a review/javítás-kör helyette történt, nem azért, mert
lezárult.
