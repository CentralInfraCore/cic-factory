# Job review — delegálási ellenőrzés

Amikor egy agent job outputját értékeled, követd ezt a sorrendet:

## 1. Olvasd el az output fájlokat

Az agent munkakörnyezetéből (`jobs/<job-id>/output/`). Csak a szöveget olvasd — ne kérdezd le a KB-t.

## 2. Döntési pont: van-e alapvető architektúrális hiba?

**Igen** → Ne kérdezd le a KB-t részletekért. Írj jobb `input.md`-t és futtasd újra az agentet.

**Nem** → Spot-check: legfeljebb 2-3 célzott KB lekérdezés egy konkrét állítás ellenőrzésére.

## 3. Ha hiányt találsz — NE te kutasd fel

A helyes reakció:
```
→ input.md frissítése: "kérdezd le X területet is"
→ agent újrafuttatása
```

A hibás reakció:
```
→ Te lekérdezed a KB-t
→ megtalálod a hiányt
→ beírod az input.md-be
→ újra ugyanez
```

## Alapszabály

> Az orchestrátor jó kérdéseket ír. Az agent válaszol.
> Ha te válaszolsz a saját kérdéseidre, kihagyod az agentet.

## Jelek hogy rossz úton vagy

- Több mint 3 KB lekérdezést teszel értékelés közben
- Az `input.md`-t a saját KB lekérdezéseid alapján bővíted
- Azt mondod "jó az anyag" anélkül hogy az output fájlokat elolvastad volna
- A workspace klón tartalmát nézed a live workdir `output/` helyett
