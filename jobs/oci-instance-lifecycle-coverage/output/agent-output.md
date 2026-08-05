# agent-output — `oci-instance-lifecycle-coverage`

## Összefoglaló

Repo: `cic-module-oracle-cloud`, branch `feature/oci-instance-lifecycle-coverage`
→ pusholva, **PR nem nyitva** (a spec szerint). Commit: `558c9571e1a2ca4`.
CI: **zöld** (`gh run view 30940946018`, `headSha` egyezik a testelt committal).

A három résre bontott feladat mindhárom pontja elkészült; a valós-OCI futtatás
(a job hatóköre szerint) az orchestrátoré maradt — lásd
`output/orchestrator-verification.md`.

## A — `cic:compute:instance` séma

Kész. `make oci.generate` mostantól három sémát állít elő
(`vcn.json`, `subnet.json`, `instance.json`); a `vcn`/`subnet` kimenet
byte-azonos maradt (nincs regresszió). A resolver a role-bridge job által már
igazolt módon oldja fel az `Instance` élettartam-műveleteit
(`LaunchInstance→create`, `TerminateInstance→delete`, `UpdateInstance→update`,
`ChangeInstanceCompartment→action`) — most már **szállított** sémaként, nem
csak scratch fixture-ként.

`describe()` `resource_kinds`-je mostantól tartalmazza `cic:compute:instance`-t
(mérve, `TestManualDescribe` kimenetéből). `required_capabilities.egress_hosts`
**nem** változott resource kind szerint — ez egyetlen statikus `*.oraclecloud.com`
wildcard a `Describe()`-ban, nincs resource-specifikus elágazás (mérve, nem
feltételezve — lásd `provider.go:165-168`).

A per-service integritás-kapu (`oci-sdk.lock.yaml`
`extracted_schema_hashes[core]`) újra-pinnelve; mindkét irányban igazolt, hogy
buknak a szándékos törések (`test_oci_sdk_lock.py` egy hamis hash-sel,
`oci-extract -diff` egy `required`-ből kivett mezővel).

## B — `Destroy()` a harnessben

Kész. `TestManualRealOCIDestroy` a valódi `Destroy()` handlert hívja — nem
`Execute()`-ot. Ez volt a job legfontosabb része: eddig minden "törlés" teszt
`Execute(OCI_EXEC_OPERATION=Delete...)`-en ment át, ami sosem futtatta a
`resolveOp`-ot és a ProofTrace-be kerülő címkét a `Destroy()` saját kódútján.

Env-guard nélkül igazoltan **nem** ad hálózati hívást (`REAL_OCI_TEST` nélkül
`SKIP`, 0.002s alatt, nincs hívás). Valós OCI ellen **nem futott** — ez a
job explicit korlátja (ne hozz létre valós OCI erőforrást), nem mulasztás.

## C — `Invoke()` a harnessben + scoping döntés

Kész. `TestManualRealOCIInvoke` létezik, ugyanúgy env-guardolt. A scoping
döntés (`output/invoke-scope.md`): az egyetlen valós invoke-célpont
`cic:compute:instance`-hoz `ChangeInstanceCompartment`, ehhez **második
compartment kell**, amivel a trial tenancy nem rendelkezik. Megvizsgáltam,
hogy egy compartment-mozgatást nem igénylő akció (pl. power state:
start/stop) kiváltaná-e ezt — **nem**: a jelenlegi extrakciós recept csak azt
az akciót veszi fel a sémába, aminek a body-modelljét a hívó explicit átadta,
és a body nélküli (query-param-alapú) akciókat egyáltalán nem kezeli. Ez egy
külön, e jobban kívül eső receptbővítés lenne — nem próbáltam megkerülni.

## D — Dokumentáció

- `docs/design/manual-verification.md`: `poll` sora **verified**-re frissítve
  (2026-08-04, `SUCCEEDED`, a `percent_complete` bug leírásával, commit
  `4e577c8` alapján); új `destroy`/`invoke` sorok (`not run`, a harness
  meglétével); új sor a `cic:compute:instance` sémáról; Usage szekció kibővítve
  a Destroy/Invoke parancsokkal; a "bare -run" figyelmeztetés frissítve mindhárom
  mutáló tesztre.
- `docs/design/roadmap.md`: P2.3 "két kind" → "három kind"; P3.4 `poll` `blocked`
  → `verified`; P3.5 kiegészítve azzal, hogy az `instance` most szállítva van,
  de ez egy lefedettség-vezérelt kiegészítés, nem P3.5-scope döntés — a
  hand-picked lista változatlan marad a todo-ként.
- `mk/golang.mk`: `oci.generate` kibővítve az Instance-generálással
  (`NET_CLIENT`/`COMPUTE_CLIENT` szétválasztással); `golang.test.manual-real-oci`
  fölött egy komment indokolja, miért nincs — szándékosan — Destroy/Invoke a
  konvencionális `-run` mintában.

## Amit NEM csináltam meg

- **Nem futtattam valós OCI ellen sem a `Destroy`-t, sem az `Invoke`-ot** — a
  job explicit tiltása. A pontos recept `output/orchestrator-verification.md`-ben
  (A: Destroy VCN-en, B: Destroy Instance-en, C: Invoke ChangeInstanceCompartment).
- **Nem bővítettem az extrakciós receptet** power-state (start/stop) instance-
  akciókra — kívül esik a job hatókörén (`Instance` séma + `Destroy`/`Invoke`
  harness, nem az extraktor bővítése).
- **Nem kötöttem be primitives/YANG sémát** és **nem nyúltam a CIC-Relay-hez** —
  mindkettő a job explicit tiltása volt; nem is volt rá szükség.

## Gépi kapuk (Definition of Done, 1–9)

Mindegyik ténylegesen lefuttatva és igazolva — a pontos parancsok és kimenetek
`output/claim-evidence.md`-ben. Rövid összefoglaló:

1. `make oci.generate` → instance.json is előáll; `-diff` kapu bukik szándékos
   törésen (mindkét irány lefuttatva) — **OK**
2. `describe()` `resource_kinds` tartalmazza `cic:compute:instance`-t, futtatott
   kimenettel — **OK**
3. Reachability: `contracts.go:24`→`:28`→`:92` → `provider.go:176`→`:158`
   production hívólánc, grep-pel igazolva — **OK**
4. `TestManualRealOCIDestroy`/`Invoke` léteznek, env-guard mögött, guard nélkül
   nincs hálózati hívás (mutatva) — **OK**
5. `vcn`+`subnet` lefedettség nem romlik, regressziós teszt zöld — **OK**
6. `make check` + wasm build/test zöld — **OK** (lásd a companion-yaml
   zavaró tényező megjegyzését `claim-evidence.md`-ben)
7. `MANIFEST.sha256` regenerálva, `manifest-verify` zöld — **OK**
8. `docs.link-check` zöld — **OK**
9. CI zöld a pusholt feature branchen, `headSha` egyezik a testelt committal
   (`558c9571e1a2ca49ae8504b512530ab4f2ae08b0`) — **OK**
