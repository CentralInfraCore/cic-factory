# A #195 spec review (cic-factory #69, HEAD 48ac711) — tulajdonosi döntések, 2026-11-16

Döntés: REQUEST CHANGES, két célzott pontosítás; a fejlesztési irányt elfogadja. A #195 iránya GO, az implementáció addig HOLD, amíg a spec nincs jóváhagyva.

## F1 — HIGH: a jóváhagyott pin-frissítés átmenete

A kizárólag a pin-fájlt módosító külön PR problémás: az új pin és a régi eszközbeállítás eltérése miatt a meglévő kapuk helyesen bukhatnak. A szabályos frissítés **atomi** változás:

- a pin módosítása;
- a hozzá tartozó telepítési konfiguráció változása;
- az egzakt PR-HEAD-hez és pin-digesthez kötött tulajdonosi jóváhagyás;
- az új eszközkészlettel elvégzett teljes ellenőrzés.

A jóváhagyás nem jelentheti a minőségi kapuk megkerülését, és új push esetén érvényét kell veszítenie.

## F2 — HIGH: a referencia és az ellenőrző mechanizmus eredete

Nemcsak a pin-fájlt kell védeni, hanem azt is, hogy melyik ellenőrző script és milyen paraméterek alapján értékel. Kötelező negatív esetek:

| Manipuláció | Elvárt eredmény |
|---|---|
| Pin és setup együttes módosítása | DENY |
| Kötelező mérőeszköz eltávolítása | DENY |
| Hamis referencia-SHA átadása | DENY |
| Ellenőrző script gyengítése | DENY vagy dokumentált védelmi rés |
| Workflow-lépés eltávolítása | dokumentált, reprodukált védelmi rés |
| Jóváhagyás utáni új push | új jóváhagyás szükséges |

Az utolsó előtti eset teljes védelme külön, repository-szintű feladat maradhat.

## Tulajdonosi döntésekre tett javaslat

| Kérdés | Javaslat |
|---|---|
| Pin-frissítés jóváhagyása | külön, célzott, aláírt és tulajdonos által jóváhagyott toolchain-update PR |
| Workflow eredetének védelme | külön kötelező feladat, a PR-07 előtt |
| Cargo mérőeszközök telepítési pinje | külön feladat |
| FULL/DIFF integráció | a referencia védelme után |

## Sorrend

#195 (pin és referenciavédelem) → workflow-eredet védelme → PR-07 (FULL/DIFF/nightly) → PR-08 → PR-09.

„Nem építenék további bizonyítási rétegeket olyan mérési alapra, amelyet maga a vizsgált PR módosíthat.”
