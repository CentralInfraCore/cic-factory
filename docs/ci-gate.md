# ci-gate — a CI figyelése és a HEAD-hez kötött lezárás

A `tools/ci-gate.py` a fejlesztői kör lezáró lépése: egy PR **pontos HEAD-jének** CI-jét figyeli, és ha a szabályzat engedi,
pontosan azt a HEAD-et mergeli. A döntést nem pótolja: a merge egy már meghozott döntés végrehajtása.

```
tools/ci-gate.py check      OWNER/REPO#N --head SHA                    # egy leolvasás: GREEN | RED | PENDING | HEAD-MOVED
tools/ci-gate.py watch      OWNER/REPO#N --head SHA [--interval 60]    # addig figyel, amíg a HEAD el nem dől
tools/ci-gate.py merge      OWNER/REPO#N --head SHA --review-closed-at SHA [--dry-run]
tools/ci-gate.py post-merge OWNER/REPO --sha MERGE_SHA                 # a merge commit CI-ja a célágon
```

## A kör

1. Implementáció → push → PR; a koordinátor feljegyzi a pontos HEAD-et.
2. `watch` fut a háttérben. **Pending** nem hiba és nem siker: nem merge-el, a fejlesztés nem áll meg.
3. **RED**: a hibás kapuk neve kiíródik; naplóelemzés, besorolás (kód, infrastruktúra, ismert tűrt eset), célzott javítás,
   új push. Az új HEAD új ellenőrzési alap, a `watch` újraindul vele.
4. **GREEN** és a szerződéses review ugyanezen a HEAD-en lezárt: `merge --review-closed-at <ugyanaz a HEAD>`.
5. Merge után `post-merge`: a `main` új HEAD-jének CI-ja. Csak ezután lezárt a munka.

## Mit tagad meg a `merge`

| Eset | Eredmény |
|---|---|
| a review más HEAD-en zárult le, mint amelyiket mergelni akarunk | REFUSED: új HEAD új review |
| bármelyik kapu pending, piros, cancelled vagy ismeretlen végeredményű | REFUSED (a cancelled **nem** siker) |
| a HEAD-en egyetlen ellenőrzés sem futott | REFUSED (nulla kapu nem zöld) |
| a HEAD azóta elmozdult | REFUSED, kilépési kód 3 |
| nem mergelhető (konfliktus, ismeretlen), zárt vagy draft PR | REFUSED |
| a két leolvasás között valami megváltozott | REFUSED |

A merge `gh pr merge --squash --match-head-commit <HEAD>`: ha a HEAD közben mozdul, a GitHub is megtagadja. Hálózati hiba
után az eszköz előbb a PR állapotát olvassa vissza, és nem próbálkozik vakon újra.

## Amit nem old meg

- A review-t nem helyettesíti és nem hamisítja: a `--review-closed-at` értékét a koordinátor csak akkor adja meg, ha a
  felhatalmazás a jóváhagyott PR-hatókörre és erre a HEAD-re szól. Szerződésváltozásnál marad a review-megálló.
- A natív GitHub `--auto` csak a kötelezőnek jelölt kapukat várja meg; ez az eszköz a HEAD **összes** ellenőrzését.
- Nem dönt el, hogy egy piros kapu infrastruktúra-hiba-e: ezt a naplóelemzés dönti el, és csak egy befejezett, sikeres
  újrafutás számít bizonyítéknak.
