# wasm-template-design — A base-repo `wasm/devel` sablon TERVE

## Reasoning mód

**audit → tervezés.** Feltérképezed a meglévő base-repo sablonokat, majd megtervezed
a WASM-repo-sablon deltáját. **Ez a job TERVET ad, nem branch-et** — a tényleges
`wasm/devel` feltöltés egy követő implementáló job dolga.

## Cél

A base-repo egy multi-branch sablon-repo: minden repo-típushoz egy sablon-branch
(`golang/devel`, `schemas/devel`, `IaC/devel`, `workflows/main`, `mcp/devel`).
**Nincs `wasm/*` branch.** Ez a job megtervezi, mi kell egy `wasm/devel` sablon-branchhez,
amelyből WASM-modul-repókat lehet gyártani — a **legfejlettebb release-folyamat**
(`schemas/devel`, a primitives alapja) mintájára.

## Kontextus — olvasd el ELŐSZÖR

### A base-repo branch-modell (klónozd: `base-repo`)
- `git branch -a` → a sablon-branchek: `golang/{main,devel}`, `schemas/{main,devel}`,
  `IaC/devel`, `workflows/main`, `mcp/devel`, `docs/main`.
- **`schemas/devel`** hozza a teljes release-pipeline-t (ezt vedd alapul):
  `make validate / release-check / release-prepare / release-close` (3-fázisú versioned
  release), Vault-signing (`tools/vault-sign-agent.sh`, `tools/finalize_release.py`),
  commit-hook (`tools/git_hook_commit-msg.sh`), `tools/compiler.py`, `tools/infra.py`
  (ReleaseManager), `tools/release.sh`, manifest-verify/update.
- **`golang/devel`** hozza a Go-toolchain + quality scripteket: `Makefile`,
  `scripts/{gen_manifest,quality,lint_local,fmt_local,ai_verify}.sh`,
  `tools/{vault-sign-agent,git_hook_commit-msg}.sh`.

### A WASM build-cél (a relay host-frame ABI-hoz kell illeszkednie)
- A relay WASM host-frame: `CIC-Relay/core/cabinet/cicwasm.go` — wazero-alapú, és egy
  **konkrét guest ABI-t vár**: exportált `allocate` / `deallocate` / `call`, a result
  packed `uint64`-ként (`(size << 32) | pointer`), a payload JSON `{data, error}`.
- Referencia guest-implementáció (kézi, nyers): `CIC-Relay/core/cabinet/testdata/echo_json.go`
  — `//go:build wasip1`, `//export allocate/deallocate/Call`, `C.malloc`. **Ezt a nyers
  boilerplate-et kell a sablonnak fejlesztő-barát formában adnia.**
- A guest contract dokumentálva: KB `c689` (iSDK API Contract v1) — `Call(op, auth, data)
  → (data, error)`, op ∈ {init, process, get, notify}, hibakódok INPUT/RUNTIME/INTERNAL/
  RESOURCE/TIMEOUT, v1 szinkron.
- **Státusz-tény:** az iSDK guest-SDK jelenleg `concept` (lásd `cic-factory/docs/relay-isdk-guest-map.md`).
  Ez a sablon lenne az iSDK **első konkrét megtestesülése** — a `allocate/deallocate/Call`
  vázat a sablon adná, hogy a modul-szerző csak az init/process/get/notify domain-logikát írja.

## Feladat — a terv elemei

### 1. Feltérképezés (bizonyítékkal)
Klónozd a `base-repo`-t, és térképezd fel `grep -rn`-nel (a `_test`-fájlokat kizárva,
`grep -v _test`) a `schemas/devel` és `golang/devel` branch tartalmát:
- mi a release-pipeline (3-fázisú), mely tool-ok adják, mi a signed artifact a schemas-ban;
- mi a Go-build és quality-réteg a golang-ban.
Minden státusz-állítást (mi `implemented`/működik a sablonban) **file:line** hivatkozással
támassz alá a claim-evidence táblában — a "fájl létezik" nem elég.

### 2. WASM-delta terv
Tervezd meg, mi a `wasm/devel` sablon a fentiek fölött:
- **Build-target döntés (explicit, indoklással):** `GOOS=wasip1` (cgo, a `cicwasm.go`/
  `echo_json.go` mintára) **vs** TinyGo. Adj ajánlást és indoklást — melyik illeszkedik a
  relay host ABI-hoz és a 3-fázisú release-hez. Ne hagyd nyitva.
- **A signed release artifact:** mi kerül aláírásra — a `.wasm`, vagy `.wasm` + meta-manifest?
  Hogyan illeszkedik a schemas 3-fázisú `release-prepare/close` mechanizmusába.
- **Guest ABI scaffold (az iSDK első váza):** a sablon `allocate`/`deallocate`/`Call`
  boilerplate-je + a domain-belépők (init/process/get/notify) üres slotjai, hogy a host
  (`cicwasm.go`) hívni tudja. Add meg a fájl-vázat (nem teljes implementáció — váz + szerződés).

### 3. Sablon-fájllista forrás-megjelöléssel
Add meg a `wasm/devel` teljes tervezett fájllistáját, minden fájlnál jelölve a forrást:
`öröklött schemas/devel-ből` | `öröklött golang/devel-ből` | `ÚJ (WASM-specifikus)`.

### 4. A követő implementáló job spec-vázlata
A terv végén add meg egy `wasm-template-impl` követő job rövid spec-vázlatát (cél, mit
rakjon a `wasm/devel`-re, DoD) — amit az orchestrátor review után konkrét job-bá tehet.

## Tiltott rövidítések (kötelező)

- **A terv ≠ működő sablon.** Ez a job nem hozza létre a `wasm/devel`-t, csak megtervezi.
- **A sablon-fájl léte ≠ működő WASM build.** A tervben jelöld, mi a verifikációs lépés
  (pl. `GOOS=wasip1 go build` zöld + a host `cicwasm.go` betölti), ne tételezd működőnek.
- **Build-target nem maradhat nyitva.** wasip1 VAGY TinyGo — döntés + indoklás kötelező.

## Output

- `jobs/wasm-template-design/output/wasm-template-plan.md` — a teljes terv +
  **claim-evidence tábla** ezekkel az oszlopokkal: `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat` (a Bizonyíték oszlop file:line). Minden feltérképezett implemented/scaffold állításhoz file:line reachability-artifact (`grep -rn` kimenet, `_test` kizárva, VAGY `deadcode ./...`).

## Definition of Done

- [ ] `schemas/devel` + `golang/devel` sablon feltérképezve, file:line bizonyítékkal
- [ ] build-target döntés (wasip1 vs TinyGo) meghozva + indokolva
- [ ] signed release artifact meghatározva + a 3-fázisú release-be illesztve
- [ ] guest ABI scaffold váza (allocate/deallocate/Call + init/process/get/notify) megtervezve, a `cicwasm.go` ABI-hoz illesztve
- [ ] teljes `wasm/devel` fájllista forrás-megjelöléssel (schemas / golang / ÚJ)
- [ ] `wasm-template-impl` követő job spec-vázlata
- [ ] claim-evidence tábla minden státusz-állításhoz file:line bizonyítékkal

## Nyelvi szabály

- Dokumentáció, terv: **magyarul**
- Kód-vázak, fájlnevek, Makefile-target, shell, YAML: **angolul**
