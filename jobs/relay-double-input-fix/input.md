# relay-double-input-fix — double-input bug javítás

## Háttér

A `relay-func-audit` és külső review is azonosította: `cmd/relay/activator.go:37`-ben a payload dupla csomagolással kerül az execution context-be.

**A hiba:**

```go
// activator.go:37
Payload: map[string]any{"input": res.Spec}
```

A `Cabinet.Setx` ezt a Payload-ot `variables["input"]`-ba teszi — így az agent `input.input.field` helyett `input.field`-et vár, de kap dupla csomagolást.

**A javítás:**

```go
Payload: res.Spec
```

A `res.Spec` már egy `map[string]any`, közvetlenül átadható.

## Forrás

```
${CIC_RELAY_PATH}/cmd/relay/activator.go
```

Olvasd el a teljes fájlt mielőtt módosítasz. Különösen ellenőrizd:
- `res.Spec` típusát — kompatibilis-e a `Payload` várt típusával
- Hol és hogyan használja a `Payload`-ot a `Cabinet.Setx` / `NewExecutionContext`

```bash
grep -rn "Payload\|NewExecutionContext\|variables\[.input.\]" ${CIC_RELAY_PATH}/core/cabinet/ --include="*.go" | grep -v "_test.go"
```

## Elvégzendő lépések

1. Olvasd el `activator.go`-t és `core/cabinet/service.go`-t (Setx, NewExecutionContext)
2. Ellenőrizd a típuskompatibilitást grep-pel
3. Módosítsd `activator.go:37`-et
4. Futtasd a teszteket:

```bash
cd ${CIC_RELAY_PATH}
COMPOSE_FILE=docker-compose.yaml docker compose up -d builder
COMPOSE_FILE=docker-compose.yaml make test-go
```

5. Ha tesztek zöldek: commit + push feature branch-re

```bash
git -C ${CIC_RELAY_PATH} checkout -b fix/double-input
git -C ${CIC_RELAY_PATH} add cmd/relay/activator.go
git -C ${CIC_RELAY_PATH} commit -m "fix(activator): remove double input wrapping in Payload"
git -C ${CIC_RELAY_PATH} push -u origin fix/double-input
```

## Output fájlok

`output/fix-report.md`:

```markdown
## Típusellenőrzés
**res.Spec típusa:** [grep eredmény]
**Payload várt típusa:** [grep eredmény]
**Kompatibilis:** igen/nem

## Módosítás
**Fájl:** cmd/relay/activator.go
**Sor:** 37
**Előtte:** `Payload: map[string]any{"input": res.Spec}`
**Utána:** `Payload: res.Spec`

## Tesztek
**Exit code:** 0 / 1
**Érintett package-ek:** [PASS/FAIL lista]

## Git
**Branch:** fix/double-input
**Commit hash:** ...
```

`output/claim-evidence.md` — Kötelező tábla:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| res.Spec típusa kompatibilis Payload-dal | true/false | grep kimenet | grep -rn futtatva | kritikus |
| módosítás elvégezve | true/false | diff | fájl olvasva | kritikus |
| tesztek zöldek | true/false | exit code + PASS sorok | make test-go futtatva | kritikus |
| változások commitolva | true/false | commit hash | git log | alacsony |

## Szabályok

- **Fájl létezése ≠ implementált** — grep-pel ellenőrizd a típusokat
- **Exit code 0 ≠ sikeres** — olvasd el a teszt kimenetét
- Ha típusinkompatibilitást találsz: ne erőltesd a javítást — rögzítsd és állj meg
- Csak `activator.go`-t módosítsd — ne nyúlj más fájlhoz
