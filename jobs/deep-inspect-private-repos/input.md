# Feladat: Négy privát repo részletes feltárása

## Kontextus

Az előző job (`map-private-source`) feltérképezte a teljes private source könyvtárat.
Ez a job négy kiemelt repót vizsgál mélyebben.

Az előző job kimenetei referenciaként:
- `${CIC_WORKDIR}/jobs/map-private-source/output/repos.yaml`
- `${CIC_WORKDIR}/jobs/map-private-source/output/overview.md`

## Vizsgálandó repók

Keresd meg ezeket a lokális fájlrendszeren (valószínű helyek: `${CIC_PARTNERS_ROOT}/`):

1. **CIC_Relay** — ProofTrace végrehajtó platform
2. **CIC_Schemas** — schema compiler, Vault signing
3. **cic-mcp-private** — privát MCP szerver
4. **github_private** — ismeretlen tartalom

## Mit kell feltárni minden repónál

- Teljes könyvtárstruktúra (3 szint mélységig)
- `go.mod` / `package.json` / `requirements.txt` — függőségek, modul név
- CI/CD: `.github/workflows/` fájlok tartalma
- Kulcsfájlok: `main.go`, `server.py`, `Makefile`, stb. — mi az entry point
- README ha van
- Git remote URL és aktuális branch/tag
- Kapcsolódás a többi CIC repóhoz (import, referencia, config)
- Mi a státusza: aktív fejlesztés / karbantartás / archív?

## Kimeneti fájlok

### `output/CIC_Relay.md`
Részletes kép: architektúra, modulok, entry pointok, függőségek, CI, státusz.

### `output/CIC_Schemas.md`
Részletes kép: schema compiler logika, Vault integráció, workflow-k, státusz.

### `output/cic-mcp-private.md`
Részletes kép: MCP szerver felépítése, eszközök, KB adat struktúra, hogyan indexel.

### `output/github_private.md`
Részletes kép: mi van benne, mire való, kapcsolódások.

### `output/connections.md`
Keresztkapcsolatok: hogyan függnek össze egymással és a többi CIC repóval.

Kimeneti path: `${CIC_WORKDIR}/jobs/deep-inspect-private-repos/output/`
