# Claim Evidence

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| staticcheck elérhető a containerben | **true** | `~/tmp/cache/CIC-Relay/go/bin/staticcheck` létezik; container log: `go: downloading honnef.co/go/tools v0.6.1` → tool letöltve és telepítve | `ls ~/tmp/cache/CIC-Relay/go/bin/` — a volume-mount miatt a host és a container `/go/bin` azonos könyvtár | közepes |
| lint-go átmegy (exit 0) | **false** | Exit code 1 — staticcheck U1000 hibát talált: `core/modules/schemapipeline/schemapipeline_test.go:27:2: field args is unused` | `make lint-go` futtatva, kimenet elolvasva | közepes |
| lint-go infrastruktúra működik | **true** | staticcheck települt és lefutott az összes package-en (23 csomag), valódi hibát adott vissza — nem "not found" hibát | `make lint-go` kimenet: `Staticcheck on: centralrelay/cmd/relay ... core/modules/schemapipeline ...` | alacsony |
| változások commitolva | **true** | Commit hash: `8d7103a` — `fix: auto-install staticcheck in lint-go if not present in /go/bin` | `git log --oneline -1` a CIC-Relay repoban | alacsony |
| változások pusholva | **true** | `origin/fix/staticcheck-setup` létrejött | `git push -u origin fix/staticcheck-setup` sikeres | alacsony |

## Megjegyzés a lint hibáról

A `U1000` (`unused code`) hiba valódi kódhiba: `schemapipeline_test.go:27`-ben az `args` struct field deklarált de nem használt. Ez nem infrastruktúra-probléma — a statikus elemzés pontosan azt csinálja amit kell. Javítás külön job-ban szükséges.
