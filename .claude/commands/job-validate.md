# job-validate — Job spec validátor

Minden agent indítás előtt kötelező futtatni. Nem az input.md szándékát értékeli — konkrét kritériumok meglétre kérdez rá.

## Futtatás

```
/job-validate <job-id>
```

## Mit csinálj

1. Olvasd el: `jobs/<job-id>/input.md`
2. Minden kritériumra: PASS / FAIL / N/A
3. Ha bármelyik kritikus kritérium FAIL → **NO-GO**, ne indítsd az agentet

---

## Kritériumok

### K1 — Forrás meghatározva (kritikus)
**Kérdés:** Explicit megnevezi-e a spec azt hogy honnan dolgozzon az agent?
- Forráskód audit → konkrét path megadva
- KB audit → konkrét chunk-ok megadva
- Mindkettő → mindkettő megadva

FAIL ha: csak "nézd meg a kódot" / "KB alapján" — path vagy node-id nélkül

---

### K2 — Státusz definíció ellenőrzési módszerrel (kritikus)
**Kérdés:** Az `implemented` / `scaffold` / `concept` definíció tartalmaz-e explicit ellenőrzési módszert?

PASS csak ha:
- `implemented` megköveteli a hívási lánc ellenőrzését (grep vagy közvetlen hívás trace)
- `scaffold` leírja a conditional bypass esetét is (`if X == nil`, `if !Flag`)
- Nem elég: "kódban él" — kell: "production kódban hívódik, grep bizonyítja"

FAIL ha: a definíció csak leírja mit jelent, de nem írja le hogyan bizonyítod

---

### K3 — Explicit tiltott rövidítések (kritikus)
**Kérdés:** Van-e legalább egy explicit "NEM fogadható el" szabály?

Példa: "fájl létezése ≠ implemented", "teszt lefedettség ≠ implemented", "KB leírás ≠ implemented"

FAIL ha: csak pozitív szabályok vannak

---

### K4 — Output formátum meghatározva
**Kérdés:** Az output fájlok neve és formátuma specifikálva van-e?

FAIL ha: csak "írj összefoglalót" — fájlnév és struktúra nélkül

---

### K5 — Tesztelhető sikeresség (közepes prioritás)
**Kérdés:** Van-e legalább egy olyan elvárás amit az orchestrátor közvetlenül ellenőrizhet?

Példa: "minden implemented mellé add meg a hívó fájlt és sort", "grep eredményt idézd a report-ban"

FAIL ha: az output ellenőrizhetetlen az agent saját állításain kívül

---

### K6 — Negatív példák (közepes prioritás)
**Kérdés:** Van-e legalább egy példa arra hogy MIT NE csináljon az agent?

FAIL ha: csak pozitív utasítások vannak

---

### K7 — Forráskód audit specifikus (csak forráskód joboknál kritikus)
**Kérdés:** Explicit megköveteli-e a call-chain grep ellenőrzést?

Elvárt minta (vagy ekvivalens):
```
grep -rn "<FüggvényNév>" --include="*.go" | grep -v "_test.go"
0 találat → scaffold
```

FAIL ha: "olvasd el a fájlokat" — grep előírás nélkül

---

## Output formátum

```
## Validáció: jobs/<job-id>/input.md

| Kritérium | Státusz | Megjegyzés |
|---|---|---|
| K1 — Forrás | PASS/FAIL | ... |
| K2 — Státusz def + módszer | PASS/FAIL | ... |
| K3 — Tiltott rövidítések | PASS/FAIL | ... |
| K4 — Output formátum | PASS/FAIL | ... |
| K5 — Ellenőrizhetőség | PASS/FAIL | ... |
| K6 — Negatív példák | PASS/FAIL | ... |
| K7 — Call-chain grep | PASS/N/A/FAIL | ... |

## Összesítés: GO / NO-GO

[Ha NO-GO: pontosan mi hiányzik, mit kell javítani]
```

---

## Ami után GO esetén következik

`/job-run <job-id>`

## Ami után NO-GO esetén következik

Javítsd az input.md-t a jelzett pontokon, futtasd újra a validátort.
Ne indítsd el az agentet amíg NO-GO áll fenn.
