# Terraform Apply Plugin implementáció

## Kontextus

**Végrehajtási modell alapelv:** A relay NEM hajt végre kódot közvetlenül. Minden konkrét műveletet — beleértve a Terraform futtatást — plugin hajtja végre `.so` fájlként, amelyet a relay `plugin.Open()` + `Lookup()` segítségével tölt be.

**KB forrás:**
- `plugin_interface.md`: "minden műveletet a dinamikusan betöltött `.so` fájlokban definiált pluginfüggvények végeznek el"
- `schema_kezeles.md`: "a séma deklarálja, melyik plugin melyik függvényét kell meghívni"
- `plugin_interface.md`: "A plugin `go build -buildmode=plugin` opcióval épül"

**Szülő job:** `poc-implementation-plan`
**Előfeltétel:** `poc-infra-setup-01` (Terraform IaC létezik)

---

## Feladat

### 1. terraform-apply plugin implementáció

**Fájl:** `plugins/terraform-apply/main.go` (CIC-Relay repo-ban)

A plugin szignatúra a relay plugin interfésznek megfelelően:

```go
// Register returns the plugin descriptor (lásd cabinet/plugin.go mintát)
func Register() PluginDescriptor { ... }

// Execute hajtja végre a Terraform műveletet
func Execute(input InputState) (OutputState, error) { ... }
```

**Bemeneti állapot (`InputState`):**
```json
{
  "terraform_dir": "/path/to/tf",
  "action": "apply|destroy|plan",
  "vars": { "key": "value" }
}
```

**Kimeneti állapot (`OutputState`):**
```json
{
  "status": "success|error",
  "actual_state": { ... },
  "terraform_output": { ... },
  "error_message": ""
}
```

**Plugin korlátai (kötelező betartani):**
- ❌ Nem tarthat fenn saját állapotot
- ❌ Nem kommunikálhat más pluginokkal közvetlenül
- ✅ Minden input explicit `InputState`-ben érkezik
- ✅ Stateless: minden hívás független

### 2. Workflow YAML definíció

**Fájl:** `plugins/terraform-apply/workflow.yaml`

```yaml
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: poc.terraform.apply
  version: 1.0.0
spec:
  steps:
    - poc.terraform-apply@1.0.0
```

### 3. Schema definíció

**Fájl:** `plugins/terraform-apply/schema.yaml`

A relay schema interfésznek megfelelő YAML:
- `PluginRef`: terraform-apply plugin
- `StateRequirement`: vault-dev futó, terraform binary elérhető
- `NextHops`: state-commit lépésre

### 4. Build szkript

**Fájl:** `plugins/terraform-apply/build.sh`

```bash
go build -buildmode=plugin -o terraform-apply.so main.go
```

### 5. Egység tesztek

A plugin teljes tesztelhetősége önállóan (relay nélkül):
- Mock Terraform binary-val futtatható
- Siker és hiba eset tesztelve
- Determinisztikus outputHash (canonical JSON)

---

## Output

`output/` könyvtárban:
- `plugin-design.md` — plugin architektúra döntések és relay interfész megfeleltetés
- `schema-yaml.md` — schema definíció magyarázattal

A tényleges Go kód a **CIC-Relay repo** `plugins/terraform-apply/` könyvtárában keletkezik.

---

## Fontos megszorítások

- A relay core (`core/cabinet/`, `cmd/relay/`) kódot NEM módosítod
- A plugin interfészt a meglévő `cabinet/plugin.go` alapján implementálod
- Canonical JSON marshalling kötelező az outputHash determinizmushoz
- Race condition mentes (go test -race)

## Nyelvi szabály
- Dokumentumok: magyarul
- Go kód, YAML, JSON: angolul
