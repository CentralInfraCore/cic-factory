# `cic-object-model` — bootstrap recept az orchestrátornak

Ez a job **nem hozott létre GitHub repót** (nincs joga hozzá). A teljes
repó-váz készen áll itt:

```
jobs/cic-object-model-spec/output/cic-object-model/
```

213 fájl, `MANIFEST.sha256`-tal együtt. Az alábbi recept ezt viszi élesbe.

---

## 0. Előfeltételek

| Mi | Ellenőrzés |
|---|---|
| Vault sign token | `test -r "$XDG_RUNTIME_DIR/vault/sign-token"` |
| Vault CA | `test -r "$XDG_RUNTIME_DIR/vault/server.crt"` |
| `hooksPath` be van állítva | `git config --get core.hooksPath` — nem üres |
| Docker + compose | `docker compose version` |
| GitHub jog a `CentralInfraCore` orgban | repo létrehozás |

---

## 1. A GitHub repó létrehozása

```bash
gh repo create CentralInfraCore/cic-object-model \
  --private \
  --description "Normative CIC object model specification, conformance vectors, and Go + Rust reference implementations"
```

**Ne** inicializáld README-vel vagy .gitignore-ral — a váz mindkettőt hozza.

---

## 2. A tartalom kihelyezése

```bash
# a live workdir gyökeréből
SRC="jobs/cic-object-model-spec/workspace/cic-factory/jobs/cic-object-model-spec/output/cic-object-model"
DST="$HOME/sync/git.partners/CentralInfraCore/cic-object-model"

# a feature branch merge-e után a live workdir-ban:
#   SRC="jobs/cic-object-model-spec/output/cic-object-model"

mkdir -p "$DST"
cp -a "$SRC/." "$DST/"
cd "$DST"

# ellenőrzés: a manifest a másolás után is stimmel
sha256sum -c MANIFEST.sha256 | grep -v ': OK$' || echo "manifest OK"
```

---

## 3. Git init és az ágstruktúra

A `cic-module-*` konvenció: munka `devel`-en, PR `main`-re.

```bash
cd "$DST"
git init -b main
git remote add origin git@github.com:CentralInfraCore/cic-object-model.git

# a base-repo mint upstream template remote — ahonnan a gépezet jött,
# és ahonnan a Renovate/template-frissítések később érkezhetnek
git remote add base git@github.com:CentralInfraCore/base-repo.git
git fetch base wasm/main

git add -A
```

### A manifest újragenerálása git ls-files alapján

A vázban lévő `MANIFEST.sha256` `find`-dal készült, mert a könyvtár még nem
volt git repó. A Makefile képlete `git ls-files`-t használ, és a `.gitignore`
kizárhat fájlokat — **a kettő eltérhet**. `git add` után regeneráld:

```bash
git ls-files -z | xargs -0 sha256sum \
  | grep -v "MANIFEST.sha256" | LC_ALL=C sort > MANIFEST.sha256
git add MANIFEST.sha256
```

> Ez `make manifest-update` docker nélküli megfelelője. Ha a builder konténer
> már fut, `make manifest-update` ugyanezt adja.

### Az első, Vault-aláírt commit

```bash
git commit -m "feat: CIC object model specification, conformance corpus and repo skeleton

SPEC.md: 34 numbered invariants covering the recursive node model, the
schema-positional structural discriminator, the four-form origin grammar and
the three-rule object closure.

conformance/: 27 implementation-independent vectors (YAML in, YAML out),
covering all 8 origin truth-table rows. Written, never executed — no
implementation exists yet.

Bootstrapped from base-repo wasm/main with the WASM machinery removed; see
docs/branch-decision.md for the measurement."

git log -1 --show-signature | head -20   # az aláírás ellenőrzése
git push -u origin main

git checkout -b devel
git push -u origin devel
```

---

## 4. Branch protection

```bash
gh api -X PUT repos/CentralInfraCore/cic-object-model/branches/main/protection \
  -f "required_status_checks[strict]=true" \
  -F "required_status_checks[contexts][]=lint_and_test" \
  -F "enforce_admins=true" \
  -F "required_pull_request_reviews[required_approving_review_count]=1" \
  -F "restrictions=null"
```

---

## 5. A gépezet ellenőrzése — ezt a job NEM tudta megtenni

**Fontos:** az alábbiakból egyetlen parancs sem futott le. Az authoring
környezetben nem volt Docker. A váz szerkezetileg konzisztens, de
**végrehajtatlan** — ez a claim-evidence tábla „nem igazolt" sorainak forrása.

```bash
cd "$DST"
export UID=$(id -u) GID=$(id -g)
mkdir -p p_venv .pip-cache

make build                 # image-ek
docker compose up -d builder
make infra.deps            # requirements.txt drift
make manifest-verify       # integritás
make docs.link-check       # belső linkek
make check                 # python/yaml quality
docker compose exec -T builder python tools/check_spec_vectors.py
```

Az utolsó parancs **futott** az authoring környezetben, docker nélkül,
`python3 tools/check_spec_vectors.py`-ként — PASS, 32/34 invariáns
vektor-fedett, 2 kimondottan nem-vektorizálható, 8/8 igazságtábla-sor fedve.
A konténerben futtatva ugyanezt kell adnia.

### Ami valószínűleg elsőre elhasal

| Tünet | Ok | Teendő |
|---|---|---|
| `make validate` hibázik | `schemas/index.yaml` még a base-repo `template-schema` meta-sémája; a `spec/*.yaml` nem ehhez készült | lásd a 7. pont nyitott kérdéseit |
| `make release` hibázik `buildHash` miatt | a `project.yaml` `buildHash: 'TBD'`, mert ebben a repóban nincs fordított artifact | a release folyamatnak a canonical source hash-éből kell töltenie |
| `docs.link-check` docker nélkül nem fut | `tools/check_doc_links.py` a konténerben él | a job host-oldali ekvivalenssel ellenőrizte: minden belső link feloldódik |

---

## 6. A sub-jobok indítása

A két implementációs sub-job spec a feature branch-en van
(`jobs/cic-object-model-go/`, `jobs/cic-object-model-rust/`). Merge után:

```bash
cd "$WORKDIR"
./tools/validate-spec.sh cic-object-model-go      # mérve: GO
./tools/validate-spec.sh cic-object-model-rust    # mérve: GO

./tools/run-job.sh cic-object-model-go cic-module-wasm-claude
```

**Sorrend számít.** A Rust job spec-je kimondottan úgy van írva, hogy a Go
implementációt csak azután nézze meg, hogy a saját spec-olvasatát leírta — a
kereszt-ellenőrzés értéke ezen áll vagy bukik. Ha a kettő párhuzamosan fut, ez
a garancia elvész.

Mindkét sub-job `workplace.repos`-a tartalmazza a `cic-object-model`-t, tehát a
`run-job.sh`-nak klónoznia kell tudnia — ezért kell a 3. lépésnek a sub-jobok
indítása **előtt** megtörténnie.

---

## 7. Nyitott kérdések, amikről neked kell döntened

Ezeket a job szándékosan nem döntötte el, mert nem az ő hatásköre:

1. **`schemas/index.yaml`** — a base-repo `template-schema` meta-sémája
   érintetlenül maradt. A `project.yaml` `canonical_source_file`-ja viszont már
   `spec/index.yaml`. A kettőt össze kell hangolni: vagy a `spec/*.yaml` álljon
   meg a `schemas/index.yaml` meta-sémája ellen, vagy a `schemas/` menjen ki és
   a `make validate` célpontja legyen a `spec/`.
2. **A migráció nyelvi tengelye** — a `docs/migration-surface.md` §0.1 megmérte,
   hogy a hat repó eltérése **kizárólag prózanyelv** (a `primitives/` angolra
   fordítva, az öt másolat magyar), 0 strukturális eltéréssel. Az egyetlen
   normatív forrás nyelve döntés, nem merge-konfliktus.
3. **A `CIC-objs` migráció ütemezése** — a `migration-surface.md` 114 fájlt
   mér, amiből ~30 igényel valódi tartalmi munkát. Külön job(ok).
4. **`docs/decision-delta.md` „Amit egy reviewernek meg kell támadnia"** — három
   pont, amit a job maga jelölt meg gyenge pontként. Ezek review-döntést
   igényelnek, nem implementációt.

---

## 8. Amit a repóba emelés NEM old meg

- **Egyetlen conformance-vektor sem futott le.** A korpusz megírva, nem
  futtatva. Ez a `cic-object-model-go` job feladata, és a spec első valódi
  próbája.
- **A `mk/rust.mk` nem létezik.** A `docs/rust-gate-extraction.md` a
  sorszámozott recept; a kiemelés a `cic-object-model-rust` jobé.
- **A D-003 / D-011 döntések nincsenek módosítva** a hat `CIC-objs` repóban. A
  `decision-delta.md` javaslat, nem végrehajtott változás. A job hard
  constraintje tiltotta a hat repó módosítását.
