# A Rust mutánsfelsorolás kapuhibájának reprodukciója (D pont)

Job: `relay-ci-parity-01-inventory` · csak mérés, javítás nincs (az PR-02).

## Vizsgált állapot

| | |
|---|---|
| CIC_Relay | ág `main`, commit `bc2c4e0a2eade4f798b51e03d2953304512960ed` |
| Toolchain | `rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8` (a `docker-compose.yml:15` pinje), `rustc 1.96.1`, `cargo 1.96.1` |
| cargo-mutants | `27.1.0` (`cargo install cargo-mutants --locked`). **A CI ennél nem pinel**: `taiki-e/install-action@v2` `tool: cargo-mutants` verzió nélkül (`mutation-pr.yml:55-57` és `:131-133`, `nightly.yml:130-132` és `:210-212`, `mutation.yml:93-96`). A mérés tehát a 27.1.0-ra érvényes, a CI aktuális verziójára nem. |
| Hol | Docker konténer, a repó **másolatán** (a klón nem módosult), `CARGO_TARGET_DIR` külön |

## A hibás sorok

```
.github/workflows/mutation-pr.yml:65   n=$(cargo mutants --workspace --list --in-diff /tmp/pr.diff | grep -c . || true)
.github/workflows/nightly.yml:146      n=$(cargo mutants --workspace --list --in-diff /tmp/since.diff | grep -c . || true)
.github/workflows/nightly.yml:148      n=$(cargo mutants --workspace --list | grep -c . || true)
```

A három workflow-lépésnek **nincs** `shell:` kulcsa, tehát a GitHub alapértelmezett `bash -e {0}` shellje fut: **pipefail nincs**.
(A `shell:` hiányát a fájlokból olvastam; a GitHub shell-alapértelmezését a dokumentáció alapján feltételezem, GitHub Actions futásban nem
mértem — `bash -e` emulálom.)

A `n` értékét a pipeline utolsó parancsa, a `grep -c .` állapota adja. `grep -c` 0 találatnál 1-es kilépési kóddal tér vissza, ezért a `|| true` kell,
hogy a **jogosan üres** felsorolás ne törje a lépést. Ugyanez a `|| true` viszont eltünteti a felsoroló `cargo mutants` kilépési kódját is: a pipeline
állapotát a `grep` adja, a `cargo mutants` hibája sehol nem látszik, és a hibaüzenet stderr-en megy, nem a `grep`-be.

## A reprodukció (nyers kimenet: `raw/d-repro-run1.txt`, `raw/d-repro-run2.txt`; scriptek: `raw/drepro.sh`, `raw/drepro2.sh`)

### 1. Három eset, amit a `cargo-mutants` maga megkülönböztet

A második, tiszta futás (`raw/d-repro-run2.txt`, stdout és stderr külön):

```
A valid, empty listing (diff applies, no mutable code): exit=0 stdout_bytes=0 stderr=[... INFO No mutants to filter ]
B failed listing (unreadable diff):                    exit=6 stdout_bytes=0
C failed listing (broken .cargo/mutants.toml):         exit=1 stdout_bytes=0
```

- **A** — a diff érvényes, de nincs benne mutálható kód: kilépési kód 0, üres stdout. Ez a jogos „nulla mutáns”.
- **B** — a `--in-diff` fájl nem olvasható: kilépési kód 6, üres stdout.
- **C** — csak a cargo-mutants konfigja hibás (`.cargo/mutants.toml`-ba tett második `exclude_re` kulcs: TOML `duplicate key`); a build és a tesztek érintetlenek: kilépési kód 1, üres stdout.
  (A hibát úgy hoztam létre, hogy másodszor is megadtam az `exclude_re` kulcsot; ez **nem** érvénytelen reguláris kifejezés tesztje.)

**A három eset a stdout-on nem különböztethető meg** (mind 0 bájt). Egyedül a `cargo mutants` kilépési kódja különbözteti meg őket.

### 2. A workflow-sor (`bash -e`, `|| true`) mindhárom esetre

```
n=0     <- A  (jogos üres)
n=0     <- B  (hiba)
n=0     <- C  (hiba; a lépés kilépési kódja: 0)
```

### 3. A következmény a tervezési döntésben

A felsorolt `n` után a workflow így dönt (`mutation-pr.yml:67-71`, `nightly.yml:150-155`): `n=0` → `shards=0` → a `rust` job feltétele
(`needs.plan.outputs.rust_shards != '0'`, `mutation-pr.yml:114`, `nightly.yml:193`) hamis → **a `rust` job `skipped`**.
Mérve a `shards` kiszámítása (`raw/d-repro-run1.txt`, 4e): `n=0 shards=0 -> rust job condition (rust_shards != '0') = SKIPPED`.

A záró kapu elfogadja a `skipped` eredményt:

- `mutation-pr.yml` `gate` job (`mutation-pr.yml:187`, `success|skipped) ;;`) — a `RUST=skipped` zöld.
- `nightly.yml` `report` job: csak `failure|cancelled` számít hibának, `skipped` nem (`nightly.yml:251`).

(Ezeket a workflow-szövegből olvastam; **GitHub Actions-ban nem futtattam le** a hibás felsorolást, ezért „a kapu zöld lesz” állítás itt
a workflow logikájának olvasata, nem futott CI-eredmény.)

### 4. Mikor ad hibás felsorolás nulla mutánst

Mérés alapján, ebben a pipeline-formában (`| grep -c . || true`) **minden** olyan esetben, amikor a `cargo mutants --list` nem ír stdout-ra, a kilépési
kódtól függetlenül:

| Eset | cargo-mutants kilépési kód | `n` |
|---|---|---|
| jogosan üres felsorolás (A) | 0 | 0 |
| nem olvasható `--in-diff` fájl (B) | 6 | 0 |
| hibás cargo-mutants konfig (C) | 1 | 0 |

Ezekre további, **nem mért** eseteket a szöveg csak feltételez, ezért nem sorolom a mért táblába: a diff nem egyezik a forrással (a cargo-mutants
`ERROR Diff content doesn't match source file` üzenetet ad, kilépési kódját nem mértem külön), a cargo-mutants telepítésének/elindításának hibája, memória-
vagy időkorlát — ezek mind ugyanabba a `|| true`-ba futnak, de nem reprodukáltam őket.

A részleges stdout esete (a felsoroló félúton hibázik) szintén **nem mért**: ott `n` a tényleges mutánsszámnál kisebb pozitív szám lenne, ami
kevesebb shardot ad; ezt ez a jelentés nem reprodukálta.

### 5. Ellenpróba: `|| true` nélkül, és `pipefail`-lel

`bash -e`, `|| true` **nélkül** (`raw/d-repro-run2.txt`):

```
A (jogos üres):  step exit code: 1
B (hiba):        step exit code: 1
```

Vagyis a `|| true` eltávolítása önmagában nem javít: a jogos üres eset is megbuktatná a lépést (a `grep -c` 0 találatnál 1-gyel tér vissza).

`bash -eo pipefail`, `|| true` **megtartva**, B eset:

```
n=0
step exit code: 0
```

A `pipefail` önmagában sem elég, ha a `|| true` marad.

### 6. Hibatűrő forma (mérve, a javítás nem része a jobnak)

A felsorolás fájlba megy, a **kilépési kódot előbb** ellenőrizzük, a darabszámot csak utána vesszük (`raw/d-repro-run2.txt` utolsó rész):

```
A: n=0 (listing succeeded)       exit=0
B: LISTING FAILED (exit 6) ...   exit=1
```

Ez azt mutatja, hogy a két eset szétválasztható; **ez nem a javítás**, a tényleges javítás és a hozzá tartozó negatív tesztek a PR-02 feladata.

## Egy első futás hibája (őszinteség)

A `raw/d-repro-run1.txt` 4b és 5. szakasza **érvénytelen**: az 5. esetben a `git checkout` a diff alapját megváltoztatta, ezért a `cargo mutants` „Diff content
doesn't match source file” hibát adott, és a „step exit code: 1” nem a jogos üres felsorolásról szólt. Ezt a `raw/d-repro-run2.txt` tiszta futása váltja ki, a
fenti 1.-6. szakaszok **csak** a második futásra (és a first run 1-3., 4a, 4c, 4e szakaszaira) támaszkodnak.

## Nem reprodukált: tényleges GitHub Actions futás

A hibás felsorolást nem futtattam GitHub Actions-ban, és nem nyitottam PR-t a CIC_Relay felé. Egy futó CI-bizonyíték (run id) a hiba kihasználhatóságára **nem
mérve**.
