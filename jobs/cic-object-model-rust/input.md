# cic-object-model-rust — a Rust referencia-implementáció és a `mk/rust.mk` kiemelése

## Ki vagy

**Te vagy a végrehajtó agent.** Te írod meg a Rust implementációt és emeled ki
a Rust quality gate-et. Nem te indítottad a jobot, és nincs mire várnod.

## Reasoning mód

**implementation** — de olvasd el a „Mi ennek a jobnak az igazi célja"
szakaszt, mert a legfontosabb szabálya ellentmond az ösztönnek.

---

## Mi ennek a jobnak az igazi célja

Ez a **második** implementáció ugyanarra a `SPEC.md`-re. A Go
(`cic-object-model-go`) már megvan.

Egy normatív spec, amit egyszer implementálnak, nem falszifikálható: az
implementáció lesz a spec, és a szöveg díszlet. **Kétszer implementálva viszont
minden eltérés bizonyíték: ahol a kettő különbözik, ott a spec kétértelmű.**

Ebből következik ennek a jobnak az egyetlen kemény szabálya:

> **Ha egy vektoron a Rust mást ad, mint a Go, az NEM automatikusan a Rust
> hibája — és tilos úgy „megjavítani", hogy megnézed, mit csinál a Go, és azt
> lemásolod.**

A helyes lépés: menj vissza a `SPEC.md`-hez. Ha a szöveg egyértelműen az egyik
viselkedést írja elő, a másik implementáció hibás — jelentsd. Ha a szöveg
mindkettőt megengedi, **az a spec hibája**, és az a legértékesebb találat, amit
ez a job termelhet.

A Go implementáció megnézése megengedett és hasznos — **de csak azután, hogy a
saját olvasatodat a specből leírtad.** A sorrend számít.

---

## Boot sequence

1. `kb_status` — elérhető a KB?
2. Olvasd el a `kb_focus` chunkjait (`c4135`, `c4255`, `c4367`). **A chunk-id
   nem stabil** — ellenőrizd a `file_path`-t; ha nem egyezik, az id elavult,
   keresd meg tartalom alapján és írd le az outputban.
   **FIGYELEM:** a szülő job megmérte, hogy a live repók D-003-a **8 atomot**
   mond (2026-05-04-én bővítve), miközben `c4255` még 7-et. A KB-snapshot ezen
   a ponton elavult. Ütközésnél a `SPEC.md` az irányadó.
3. A `cic-object-model` repóban, ebben a sorrendben:
   - `SPEC.md` — **egyben, elejétől a végéig**
   - `conformance/README.md` — vektorformátum, `templates:` konstrukció
   - `docs/spec-vector-map.md`, `docs/decision-delta.md`
   - `docs/rust-gate-extraction.md` — a `mk/rust.mk` receptje
4. Olvasd végig mind a 27 vektort.
5. **Csak ezután** nézd meg `go/`-t és a `cic-object-model-go` job
   `output/spec-defects.md`-jét.

**Amíg az 1–4 nem történt meg, ne írj Rust kódot és ne nyisd meg a `go/`-t.**

---

## A feladat

### A) `mk/rust.mk` kiemelése

A CIC ökoszisztémában **nincs Rust sablon**: a `base-repo`-ban nincs `rust/*`
ág, és `mk/rust.mk` sehol nem létezik. Az egyetlen Rust build/quality gépezet
**inline** él itt:

```
/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Relay/Makefile
```

A `docs/rust-gate-extraction.md` sorszám szerint megadja, mit kell kiemelni
(a szülő job 2026-08-07-én a forrás olvasásával ellenőrizte a sorszámokat, nem
grepből következtetett). A lényeg:

| Mit | Hol |
|---|---|
| `RUST_IMAGE_DIGEST` | `CIC-Relay/Makefile:46` |
| a tényleges pin | `CIC-Relay/docker-compose.yml:15` (`x-rust-version` anchor) |
| `rust-builder` service | `CIC-Relay/docker-compose.yml:119-136` |
| `RUST_EXEC` | `CIC-Relay/Makefile:114-118` |
| fmt/clippy/test/coverage/deny | `CIC-Relay/Makefile:310-351` |
| `RUST_COV_MIN ?= 90` | `CIC-Relay/Makefile:328-329` |

**Csapda, amit a recept külön kiemel:** a digest NEM a Makefile-ban van, hanem
a `docker-compose.yml` anchorában; a Makefile csak kigrepeli. Ha csak a
Makefile-sort emeled ki, a `RUST_IMAGE_DIGEST` **csendben üres string lesz** —
a `$(shell grep ...)` nem hibázik, csak nem talál semmit. Ellenőrizd, hogy a
`docker compose config` a pinnelt digestre oldódik fel.

**Amit NEM szabad kiemelni:** a `cic-ffi` / `libcic_ffi.a` gépezetet
(`Makefile:362, 396, 420, 549`). Az a relay FFI-határa. Itt a Go és a Rust
**két független implementáció ugyanarra a specre**, nem egy bináris két fele —
ha összelinkelnéd őket, pont a kétszeres implementáció értelmét semmisítenéd
meg.

### B) A materializer Rustban

`rust/` alá, cargo workspace-szel. A `SPEC.md` §8 pipeline-ja, lépésenként
elkülönítve. A lépéssorrend **normatív**: minden `expected-error.yaml` megadja
a `stage:` mezőt, és a helyes hibakód rossz szakaszban bukás.

### C) A vektorfuttató

Ugyanaz a 27 vektor, ugyanaz a korpusz, **nulla Rust-specifikus fixture**.
Vektoronként külön teszt, hogy a bukás megnevezze magát.

### D) INV-032 — a típus-szintű garancia

`SPEC.md` INV-032: `Validated<Canonical<CICObject>>` csak a core materializer
által legyen előállítható. Ez a `docs/spec-vector-map.md`-ben kimondottan
**„nem vektorizálható"** — egy YAML fájl nem tudja bizonyítani, hogy egy típus
nem konstruálható.

Rustban ez privát mezős newtype + `compile_fail` doctest:

```rust
/// ```compile_fail
/// let o = cic_object_model::Validated(raw);   // must not compile
/// ```
```

A `compile_fail` doctest **lefutását** mutasd meg (`cargo test --doc` kimenet),
ne csak azt, hogy a fájlban ott van.

### E) A kereszt-ellenőrzés — ez a job lényege

`docs/cross-implementation-report.md` a `cic-object-model` klónodban:

| Vektor | Go output | Rust output | Egyezik? | Ha nem: a SPEC melyik mondata dönt? | Verdikt |

Verdikt kategóriák:
- **Go hibás** — a spec egyértelmű, a Go tér el
- **Rust hibás** — a spec egyértelmű, én tértem el (javítottam)
- **SPEC kétértelmű** — mindkét viselkedés megfelel a szövegnek → `docs/spec-defects.md`

**Ha minden vektoron egyezik a kettő, azt is mondd ki** — az érdemi eredmény,
nem üres sor.

---

## Tiltott rövidítések

- **A fájl létezése ≠ implemented.** Egy `mk/rust.mk`, ami létezik, nem gate —
  a lefutott clippy teszi azzá.
- **`cargo build` sikere ≠ működik.** A fordítás nem viselkedés.
- **`exit code 0` a `make rust.quality`-től ≠ sikeres gate**, ha a konténer el
  sem indult. A `RUST_IMAGE_DIGEST` feloldott értékét **másold be** az outputba.
- **`exit code 0` a teszttől ≠ sikeres**, ha 0 vektor futott. A vektorszámot
  mondd ki: futott / átment / bukott.
- **Az `#[ignore]`-olt teszt nem átmenő teszt.**
- **A Go viselkedésének lemásolása nem megoldás** — lásd a job célját.
- **Az „exportált szimbólum létezik" ≠ „a production hívja".** Rustban:
  `cargo public-api` vagy `grep -rn 'pub fn'` a `src/`-ben, teszt-modulok
  kizárásával; Go oldalon a `deadcode ./...` output vagy production call site
  (file:line) az irányadó.

## Hard constraintek

1. **A `CIC-Relay` repót SOHA ne módosítsd.** Olvasási referencia. Ha hibát
   találsz benne, azt jelezd az outputban — ne javítsd, és ne kerüld meg azzal,
   hogy a logikáját ide duplikálod.
2. **Ne módosítsd a `SPEC.md`-t, a `conformance/` vektorokat és a
   `docs/spec-vector-map.md`-t.** Ha hibásak, azt jelentsd.
3. **Ne módosítsd a `go/`-t.** Ha a Go hibás, az `cross-implementation-report.md`
   sor, nem a te javításod — külön job dönt róla.
4. **Ne módosítsd a hat `CIC-objs` repót** (`primitives-group/` alatt).
5. **Ne hozz létre GitHub repót**, és ne nyiss PR-t.

---

## DoD

| # | Amit teljesíteni kell | Mivel igazolod |
|---|---|---|
| 1 | `mk/rust.mk` létezik és fut | `make rust.lint` kimenete, amiből látszik, hogy a clippy végigment a crate-en |
| 2 | A pinnelt digest feloldódik | `docker compose config` kimenetéből a `rust:1.96.1-bookworm@sha256:...` sor |
| 3 | `make rust.coverage` a mért százalékot mutatja `RUST_COV_MIN` ellen | a parancs kimenete |
| 4 | Mind a 27 vektor lefut | futott / átment / bukott szám + teszt-nevek |
| 5 | INV-032 `compile_fail` doctesttel kikényszerítve | `cargo test --doc` kimenete |
| 6 | `docs/cross-implementation-report.md` mind a 27 vektorra sort ad | fájl + sorszám |
| 7 | Minden eltérés besorolva (Go hibás / Rust hibás / SPEC kétértelmű) | ua. |
| 8 | `docs/spec-defects.md` bővítve, vagy kimondva, hogy nincs új találat | fájl |

**Amit nem tudsz igazolni, az a claim-evidence táblában „nem igazolt" sorba
megy.** Ha egy DoD-pont a spec hibája miatt teljesíthetetlen, azt **mondd ki**.

---

## Output

A `jobs/cic-object-model-rust/output/` alá, a cic-factory klónodban:

### `output/agent-output.md`
Mit csináltál, mit nem, és miért. A kiemelés és a kereszt-ellenőrzés
összefoglalója ide jön.

### `output/claim-evidence.md`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |

Minden DoD-pont egy sor.

### `output/rust/`
A teljes Rust implementáció.

### `output/mk-rust.mk`
A kiemelt gate, ahogy a `cic-object-model` repóba kerül.

### `output/cross-implementation-report.md`
A 27 vektor Go↔Rust összevetése — ez a job legfontosabb terméke.

---

## Git

- A cic-factory klónodban dolgozol, `feature/cic-object-model-rust` ágon.
- Commitolj és pushold a feature branchre. **PR-t ne nyiss**, `main`-re ne pushold.
- A `CIC-Relay` klónba **ne commitolj** — olvasási referencia.

## Nyelvi szabály

- Rust kód, komment, `mk/rust.mk`, `docs/*.md` a repóban: **angolul**
- `output/agent-output.md`, `output/claim-evidence.md`: **magyarul**
