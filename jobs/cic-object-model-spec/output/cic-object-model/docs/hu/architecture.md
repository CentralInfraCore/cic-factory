# Architektúra áttekintés

Ez a repó egy **specifikációs repó**. Az elsődleges terméke dokumentum, nem
bináris: a [`SPEC.md`](../../SPEC.md) definiálja a CIC objektummodellt, és
minden más azért van itt, hogy ezt a dokumentumot őszintén tartsa.

## A három réteg

| Réteg | Szerep |
|---|---|
| `SPEC.md` | A hivatkozási alap. Normatív, RFC 2119 nyelv, számozott invariánsok. |
| `conformance/` | A falszifikálható rész. YAML be, YAML ki — implementáció-független. |
| `go/`, `rust/` | Ugyanannak a dokumentumnak két alárendelt implementációja. |

## Miért két implementáció

Egy normatív spec, amit egyszer implementálnak, nem falszifikálható: az
implementáció csendben a speccé válik, a szöveg pedig díszletté. Kétszer
implementálva viszont minden eltérés bizonyíték — ahol a kettő különbözik, ott
a spec kétértelmű volt.

Ezért él mind a négy artifact egy repóban. Egy szemantikai változás egyetlen
változásként érkezik (SPEC + vektorok + Go + Rust), így fizikailag kényelmetlen
az egyik implementáció viselkedését úgy megváltoztatni, hogy a korpusz és a
másik implementáció ne vegye észre.

## A CI kapuk

| Kapu | Mit véd |
|---|---|
| `check_spec_vectors.py` | a SPEC és a korpusz nem csúszhat szét — invariáns nem létezhet vektor vagy leírt indoklás nélkül |
| `manifest-verify` | repó-integritás (`MANIFEST.sha256`) |
| `docs.link-check` | a belső dokumentáció-linkek feloldódnak |
| `golang.quality` / `rust.quality` | implementációnkénti quality gate |
| `make conformance` | implementációk közti egyezés; **hibával áll le, nem üresen zöldell, ha nincs implementáció** |

Az utolsó pont szándékos. Egy vektorkorpusz, ami sikert jelent, miközben nincs
mit futtatnia, rosszabb, mint ha nem lenne korpusz.

## Örökölt gépezet

A build rendszer (Docker builder, `mk/`, Vault release-aláírás,
manifest-integritás) a `base-repo` `wasm/main` ágáról származik, a
WASM-specifikus részek eltávolításával. A választás mérési háttere:
[`branch-decision.md`](../branch-decision.md).
