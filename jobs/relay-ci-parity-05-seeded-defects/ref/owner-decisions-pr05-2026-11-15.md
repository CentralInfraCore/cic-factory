# Tulajdonosi döntés a PR-05-höz (2026-11-15)

Forrás: a tulajdonos beillesztett üzenete a PR-04 lezárása után. Szó szerinti átvétel (a záró értékelő bekezdés kihagyásával).

**Az 1. opciót választanám: PR-05, de az objektumazonosság ellenőrzése kötelező elfogadási feltétel legyen.**

Nem indokolt külön PR-04b, mert a feltárt hiányosság kiváló negatív kontroll a CI önteszteléséhez.

### PR-05 – kötelező seeded defect esetek

| Szándékosan előidézett hiba | Elvárt eredmény |
|---|---|
| Objektum törlése | L3 FAIL |
| Nem létező objektum beszúrása | L3 FAIL |
| Objektum cseréje változatlan darabszám mellett | L3 FAIL |
| Objektum duplikálása | L3 FAIL |
| Mérési eredmény manipulálása | L1 FAIL |
| Más commitból származó evidence | L2 FAIL |
| Hamis vagy eltérő bemeneti digest | L2 FAIL |
| Hiányzó kötelező mérési eredmény | FAIL |
| Nemdeterminisztikus mérés | Nem minősíthető stabil bizonyítéknak |

### További követelmények

- Független Rust-objektumleltár kialakítása.
- Go és Rust esetében halmazazonosság vizsgálata, nem pusztán darabszám-egyezés.
- A három nemdeterminisztikus Go-objektum kivizsgálása.
- Minden negatív kontroll mellett legyen pozitív kontroll.
- A seeded defect tesztek automatikusan legyenek futtathatók.
- A meglévő kapuk és küszöbértékek nem gyengíthetők.
- L3 csak igazolt teljesség esetén válhat `PASS` állapotúvá.

**GO a PR-05 job-spec elkészítésére, HOLD az implementációra a spec review-jáig.**

A PR-03 újragenerálható `target-full` könyvtárának törlését támogatom, a backup ág maradjon meg. A `meta.yaml` státuszokat továbbra is tulajdonosi hatáskörben kezeljük.
