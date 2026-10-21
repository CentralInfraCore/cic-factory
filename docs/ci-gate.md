# ci-gate — a CI figyelése és a HEAD-hez kötött lezárás

A `tools/ci-gate.py` a fejlesztői kör lezáró lépése: egy PR **pontos HEAD-jének** CI-jét figyeli, és ha a szabályzat engedi,
pontosan azt a HEAD-et mergeli. A döntést nem pótolja: a merge egy már meghozott döntés végrehajtása.

```
tools/ci-gate.py check      OWNER/REPO#N --head SHA --require-from tools/ci-required/<repo>.txt
tools/ci-gate.py watch      OWNER/REPO#N --head SHA --require-from FILE [--interval 60]
tools/ci-gate.py merge      OWNER/REPO#N --head SHA --require-from FILE --approver LOGIN [--approver ...] [--dry-run]
tools/ci-gate.py post-merge OWNER/REPO --sha MERGE_SHA                 # a merge commit CI-ja a célágon
```

## A kör

1. Implementáció → push → PR; a koordinátor feljegyzi a pontos HEAD-et.
2. `watch` fut a háttérben. **Pending** nem hiba és nem siker: nem merge-el, a fejlesztés nem áll meg.
3. **RED**: a hibás kapuk neve kiíródik; naplóelemzés, besorolás (kód, infrastruktúra, ismert tűrt eset), célzott javítás,
   új push. Az új HEAD új ellenőrzési alap, a `watch` újraindul vele.
4. **GREEN** és a jóváhagyás ugyanerre a HEAD-re szól, **GitHubról olvasva**: `merge ... --approver <login>`.
5. Merge után `post-merge --require-from tools/ci-required/<repo>.post-merge.txt`: a merge commit **teljes** készlete (a mutációs
   shardokkal és az összesítő kapuval együtt) sikeres-e. Csak ezután lezárt a munka.
6. `late-advisory`: mit mondtak a végül a merge előtt nem várt (advisory) kapuk. Egy későn érkező hiba nem akadályozza meg a már
   megtörtént merge-et, de **kötelezően hibajegyet** kap (a parancs kiírja a `gh issue create` sort, de nem nyitja meg).

## Az elvárt kapuk: név szerint

A `--require-from` fájl soronként egy ellenőrzés nevét tartalmazza (`#` komment). Mindegyiknek **jelen kell lennie** a HEAD-en,
befejezve és sikeresen. Amelyik még nem jelent meg, az `PENDING` (nem zöld): egyetlen kész ellenőrzés nem elég, hanem a teljes
készlet kell, tehát nem lehet idő előtt `GREEN` egy HEAD, amelyiknek a többi kapuja még nem is jelent meg. Bármelyik ellenőrzés
hibája, akár nem elvárté is, `RED`. Üres készletet az eszköz visszautasít.

Ez **nem** ugyanaz, mint a véglegesen zöld CI: az advisory kapuk eredményét a merge már nem várja meg; ezért kell a `post-merge` teljes
készlete és a `late-advisory`. `advisory: ELŐTAG` sor: a hosszú (mutációs) ellenőrzéseket nem várjuk meg. Futás közben nem tartják pendingben a HEAD-et, egy
`cancelled` figyelmeztetés és nem bizonyíték, de egy **valódi hiba** megáll. A Forms profilja: `tools/ci-required/cic-primitive-forms.txt`.

## A jóváhagyás: a GitHubról olvasva, HEAD-hez kötve

Nem a hívó paramétere. A `--approver` bejelentkezési nevek valamelyikétől kell lennie: egy `APPROVED` review pontosan erre a
commitra (`commit_id`), vagy egy hozzászólás, amelyben van egy `merge-approved: <teljes HEAD SHA>` sor. Az utolsó döntés számít:
egy későbbi `CHANGES_REQUESTED`/`DISMISSED` review vagy `merge-revoked: <sha>` hozzászólás visszavon. Másik HEAD jóváhagyása
nem vihető át az újra. Idegen felhasználó jóváhagyása nem számít. Az eszközt futtatónak ezért nem lehet magának jóváhagyást
adnia, ha nem ő az approver.

## Mit tagad meg a `merge`

| Eset | Eredmény |
|---|---|
| nincs jóváhagyás ezen a HEAD-en az approverektől (vagy visszavonták) | REFUSED |
| az elvárt készletből valami hiányzik, fut, vagy bármi piros, cancelled vagy ismeretlen végeredményű | REFUSED (a cancelled **nem** siker) |
| a HEAD azóta elmozdult | REFUSED, kilépési kód 3 |
| nem mergelhető (konfliktus, ismeretlen), zárt vagy draft PR | REFUSED |
| a két egymás utáni leolvasás között a HEAD, az állapot, a draft, a mergelhetőség, a célág commitja vagy a kapuk eredménye változott | REFUSED |

A merge `gh pr merge --squash --match-head-commit <HEAD>`: ha a HEAD közben mozdul, a GitHub is megtagadja. Azonos nevű eredmények (újrafutás, két alkalmazás) közül a legrosszabb számít, egyet sem dobunk el. Hálózati hiba
után az eszköz előbb a PR állapotát olvassa vissza, és nem próbálkozik vakon újra.

## Amit nem old meg

- A natív GitHub `--auto` csak a kötelezőnek jelölt kapukat várja meg; ez az eszköz a **megnevezett** készletet.
- Nem dönt el, hogy egy piros kapu infrastruktúra-hiba-e: ezt a naplóelemzés dönti el, és csak egy befejezett, sikeres
  újrafutás számít bizonyítéknak. Az `advisory` kapu nem várt, de nem is némított.
- Az approver listát és a kapukészletet a repó szabályzata adja; az eszköz nem találja ki.
