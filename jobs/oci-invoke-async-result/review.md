# review — oci-invoke-async-result

- Reviewer: orchestrátor (claude-opus-5)
- Dátum: 2026-08-05
- Feature branch: `feature/oci-invoke-async-result` (cic-factory + cic-module-oracle-cloud)
- Review-zott commit: `17c85497bbd092d651d51a5dbf311674a8aaf0ef` (modul repo)

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | GO | indítás előtt futott (K1–K11) |
| `tools/validate-output.sh` | GO | 2 WARN: O1 — az `input.md`-ből hiányzik a `## Output` szekció (ez az **én** spec-hibám, nem az agenté); O5 — 12/12 `file:line` feloldhatatlan, mert a `ROOTS` (`validate-output.sh:127-130`) nem ismeri a modul repót. Kézzel feloldottam, lásd lent |
| CI (modul repo) | zöld | `gh run list --branch feature/oci-invoke-async-result` → `success`, headSha `17c8549…` — **egyezik** a review-zott committal |

## Amit ténylegesen ellenőriztem

| Állítás az outputban | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| CI zöld, headSha egyezik | saját `gh run list --json headSha,conclusion` | `success` / `17c85497bbd092d651d51a5dbf311674a8aaf0ef` = `git rev-parse HEAD` — **igazolt** |
| `operationResult` kapott `work_request_id`-t | `git diff origin/devel..HEAD -- module/provider.go` | `:638` — `WorkRequestID string \`json:"work_request_id,omitempty"\`` — **igazolt** |
| `Invoke()` `accepted`-et ad async esetben | ugyanaz a diff, `:678-693` | `switch` három ággal: `>=400` → `failed`; `WorkRequestID != ""` → `accepted`; egyébként `succeeded` — **igazolt** |
| „ugyanaz a szabály, mint a másik kódúton" (a spec ezt kérte) | `sed -n '950,985p'` + `grep -n "async"` | `Execute` az `async`-ot **kizárólag** `step.WorkRequestID != ""`-ből állítja (`:971-977`), `Destroy` a `:610-611`-ben ugyanígy. Az `Invoke` új szabálya **azonos** — nem talált ki újat — **igazolt** |
| Három új fixture létezik és zöld | `docker compose exec builder go test -run "TestInvoke\|TestDestroy" -v` | `TestDestroy`, `TestDestroyNotFoundKeepsProviderCode`, `TestInvoke`, `TestInvokeAsync`, `TestInvokeFailedStatusUnchanged` — mind PASS — **igazolt** |
| **A negatív irány** (DoD 4): a tesztek buknak a javítás nélkül | **magam állítottam vissza a hibát** és lefuttattam, majd visszaállítottam az eredetit (`git status` üres utána) | `TestInvokeAsync` → `FAIL: status = "succeeded", want accepted` + `work_request_id = "", want the header value`; `TestDestroyNotFoundKeepsProviderCode` → `FAIL: provider_code = "", want the OCI code verbatim` — **igazolt, nem az agent állításából** |
| B feladat: a 404 megőrzi az OCI kódját | diff `:598-605` | `pe := ociError(status, respBody)`, az üzenet `"resource already gone: <ocid> (<OCI üzenete>)"`, a `Class` marad `not-found`, az envelope-alak marad — **igazolt** |
| Reachability: production kódút éri el az `Invoke()`-ot | `grep -rn "Invoke(auth" module/*.go \| grep -v _test.go`, `head -1 module/abi.go` | egyetlen hívó: `abi.go:49`; `abi.go` `//go:build wasip1` → a `module.wasm`-ba fordul, amit a relay wazero hosztja hív; `provider_test.go` `//go:build !wasip1` — **igazolt** |
| A doc **nem** lett hamisan `verified` | `git diff -- docs/design/manual-verification.md` | az `invoke` sor: „**verified, with a defect (fix landed, not yet re-verified against real OCI)**", és kimondja, hogy fixture-szintű — **igazolt, a korlátot betartotta** |
| `.gitignore` `*.pem` szabály | `git diff -- .gitignore` | felvéve, indoklással, a `mk/golang.mk` csapdájára hivatkozva — **igazolt** |
| `make check`/`quality`/`wasm.*`/`manifest-verify`/`docs.link-check` zöld | nem futtattam újra lokálisan | **nem igazolt közvetlenül** — a CI zöld a pontos committon, ami ezek nagy részét lefedi |
| A commit nem szennyezett (nincs companion-yaml) | `git diff --stat origin/devel..HEAD` | 7 fájl, mind szándékos — **igazolt** |

## Amit NEM ellenőriztem

- A `manual-verification.md` és az `orchestrator-verification.md` **minden** módosított
  sorát — az `invoke` sort és a Usage-receptet néztem, a többit nem.
- A `module.wasm` binárist a `project.yaml` `buildHash`-hez (a CI futtatja).
- Az `orchestrator-verification.md` receptjét **nem futtattam le** — az a következő lépés.
- A B feladat üzenet-formátumát (`"... (<OCI üzenete>)"`) nem vetettem össze azzal,
  hogy egy ProofTrace-fogyasztó parse-olja-e ezt a zárójeles alakot. Ha valaki az
  üzenetre illeszt, ez a változás érintheti — nem néztem meg, van-e ilyen fogyasztó.

## Egy hiba a specben, amit az agent talált meg — nem az agent hibája

A DoD 3. pontja azt kérte, hogy a `>= 400` ág „továbbra is `failed` + helyes
`error_class` és `provider_code`". **Ez a saját specem hibája:** az
`operationResult`-nak sosem volt `error_class`/`provider_code` mezője (az a
`executionStep` alakja), és az A.4 hard constraint kimondta, hogy ezt az ágat ne
változtassa. A két előírás ütközik.

Az agent a hard constraintet követte, és a claim-evidence táblában **kimondta**,
hogy a DoD 3 szó szerinti olvasata nem teljesül — „flagging rather than silently
narrowing". Pontosan ezt a viselkedést akarjuk: a spec ellentmondását jelezni
kell, nem feloldani úgy, hogy közben a claim igaznak látszik.

**Tanulság a következő spechez:** a DoD-pontokat a *célstruktúra* mezőire kell
írni, nem egy másik kódút alakjára emlékezetből.

## Döntés

**MERGE** — mindkét feladat (A és B) elkészült, a lényegi állítás
(`accepted` + `work_request_id` async esetben, a meglévő szabállyal azonos módon)
forráskódszinten és futtatott teszttel is ellenőrizve, a negatív irányt **magam
mértem meg**, a reachability valós production kódútra mutat, és a doc nem állít
többet, mint amit fixture bizonyít. A valós OCI újraverifikáció nyitott tétel,
nem a merge blokkolója.
