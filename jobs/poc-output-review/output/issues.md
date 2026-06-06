# Eltérések — poc-implementation-plan

## 1. Relay definíció csonkítása (c2589 hivatkozás)

- **Mi az eltérés:** Az execution-model.md a relay-t "sémaérzékeny végrehajtási csomópontként" pozicionálja (c2589 hivatkozással), de kihagyja a c2589 KB-definíciójának lényeges elemeit: az infrastruktúra-objektumon való alkalmazás szerepét, az eredmény-továbbítást más komponensek felé, és a DAG-láncolhatóságot.
- **KB forrás:** c2589 — `./source/CentralInfraCore/CIC-basic-knowledge/docs/hu/reality/relay.md`
  > "alkalmazza az érintett infrastruktúra-objektumon, továbbítja az eredményt más komponensek (pl. állapotfigyelő, generátor) felé. A relay-ek láncolhatók: egyik relay kimenete lehet a másik bemenete. Így irányított gráf (DAG) szerű logika valósul meg."
- **Output forrás:** execution-model.md — "1. A relay pontos pozíciója" bekezdés, első felsorolás
- **Javaslat:** Elfogadható eltérés. Az output a relay "mit nem csinál" és "hogyan vezérli a workflow-t" oldalára fókuszál (c912, c914), ami a PoC kontextusban érthető hangsúlyozás. A c2589-es hivatkozás nem pontatlan, csak csonkított. Nem szükséges újrafuttatás — elegendő egy megjegyzés, hogy a relay forwarding/DAG szerepe az execution-model.md-ből hiányzik.

---

## 2. PARTIAL — drift osztályozás terminológiai eltérés

- **Mi az eltérés:** Az execution-model.md táblázatban a második drift osztály neve `RECONCILIABLE` (csonkítva), míg a KB (c2542, c2543) következetesen `RECONCILIABLE_DRIFT` (enum) / `Reconciliable Drift` (megjelenítési név) nevet használ.
- **KB forrás:** c2542 — `./source/CentralInfraCore/CIC-basic-knowledge/docs/hu/reality/drift_taxonomy.md` ("Reconciliable Drift"), c2543 ("RECONCILIABLE_DRIFT")
- **Output forrás:** execution-model.md — "2.2 fázis" drift osztályok táblázat, `RECONCILIABLE` sor
- **Javaslat:** Elfogadható, kosmetikus eltérés. A tartalom helyes. Nem szükséges újrafuttatás.

---

## 3. PARTIAL — cic-primitives "implemented" státusz részleges alátámasztottsága

- **Mi az eltérés:** A status-matrix.md a cic-primitives meta-séma réteget `implemented`-ként jelöli (c2672, c2765 alapján), de a KB-ból nem derül egyértelműen ki, hogy mind a 7 atomi primitív kódbeli Go implementációval és CI-tesztekkel fedett. A c2765 csak a meta yaml file (dokumentált koncepció), c2672 csak a README.
- **KB forrás:** c2765 — meta yaml (koncepció leírás), c2672 — README, c2801 — managed-entity.yaml (YAML séma, nem Go kód)
- **Output forrás:** status-matrix.md — "cic-primitives meta-séma réteg" sor
- **Javaslat:** Ellenőrzést igényel. Ha a primitívek csak YAML sémák (nem Go runtime), akkor a státusz `scaffold` lenne pontosabb. Ha van Go implementáció és CI lefedettség, az implemented indokolt. Javasolt: a status-matrix.md szerzőjével tisztázni, vagy a CIC-objs repóban kódreferenciát keresni.
