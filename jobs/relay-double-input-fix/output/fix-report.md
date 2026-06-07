## Típusellenőrzés

**res.Spec típusa:** `map[string]interface{}` — `types.ResourceSpec.Spec` mező (nexus/types/types.go:89)
**Payload várt típusa:** `map[string]any` — `cabinet.SetPayload.Payload` mező (set_schema.go:20)
**Kompatibilis:** igen (`map[string]interface{}` == `map[string]any` Go 1.18+)

## Módosítás

**Fájl:** cmd/relay/activator.go
**Sor:** 37
**Előtte:** `Payload: map[string]any{"input": res.Spec}`
**Utána:** `Payload: res.Spec`

A komment is frissítve: "wraps res.Spec as the payload" → "passes res.Spec directly as the payload"

### Lánc magyarázat

A hiba oka:
- `activator.go:37`: `Payload = {"input": res.Spec}` — dupla csomagolás
- `service.go:156`: `NewExecutionContext(in.Payload)` — az egész Payload-ot átadja
- `service.go:47`: `ec.variables["input"] = initialPayload` — beállítja `input` = `{"input": res.Spec}`
- Eredmény: agent `input.input.field`-re vár, de `input.field`-et próbál olvasni

A fix után: `Payload = res.Spec`, tehát `variables["input"] = res.Spec` → `input.field` helyes.

## Teszt frissítés

`activator_test.go` — `TestCabinetActivator_Activate_PayloadMapping` teszt a régi (bugos) viselkedést
ellenőrizte (`Payload["input"]` létezése). A teszt frissítve a helyes viselkedésre:
```go
// régi (bugos):
input, ok := capturedPayload.Payload["input"]
require.True(t, ok)
assert.Equal(t, spec, input)

// új (helyes):
assert.Equal(t, spec, capturedPayload.Payload)
```

## Tesztek

**Exit code:** 0
**Érintett package-ek:**
- `centralrelay/cmd/relay` — PASS
- `centralrelay/core/cabinet` — PASS
- `centralrelay/core/modules/certselfsigned` — PASS
- `centralrelay/core/modules/cibuild` — PASS
- `centralrelay/core/modules/schemacompile` — PASS
- `centralrelay/core/modules/schemapipeline` — PASS
- `centralrelay/core/nexus/crypto` — PASS
- `centralrelay/core/nexus/git` — PASS
- `centralrelay/core/nexus/iac` — PASS
- `centralrelay/core/nexus/isolation` — PASS
- `centralrelay/core/nexus/operator` — PASS
- `centralrelay/core/nexus/recorder` — PASS
- `centralrelay/core/nexus/sync` — PASS
- összes többi pkg — PASS

## Git

**Repo:** CIC-Relay
**Branch:** fix/double-input
**Commit hash:** 0ed1fed196d08c29ff0a99d0e6aed14be8b051f9
**Módosított fájlok:** cmd/relay/activator.go, cmd/relay/activator_test.go
