# Agent runner szerződés

A factory nem tudja, milyen agentet futtat. Egy **runner** az a csere-darab, ami
tudja.

Ez teszi a magot maggá: a lifecycle, a kapuk és a bizonyíték-lánc függetlenek
attól, hogy Claude Code, egy másik CLI-agent vagy egy távoli szolgáltatás végzi
a munkát.

---

## Mi a runner

Egy futtatható fájl a `tools/runners/<név>.sh` néven. A `run-job.sh` a
`CIC_AGENT_RUNNER` környezeti változóból választ (alapértelmezés: `claude`).

A runner **környezeti változókból kap** mindent, és **egy normalizált JSON-t ír**
oda, ahová mondják. Semmi mást nem kell tudnia a factory-ról.

---

## Bemenet — környezeti változók

| változó | mit |
|---|---|
| `CIC_PROMPT_FILE` | a prompt szövege fájlban (nem argumentumban — hosszú lehet) |
| `CIC_RESULT_JSON` | ide kell írni a normalizált eredményt |
| `CIC_RUN_LOG` | ide megy a runner stderr-je |
| `CIC_AGENT_CONFIG` | az agent izolált config könyvtára, ha értelmezhető |
| `CIC_MODEL` | kért modell, vagy üres |
| `CIC_MAX_TURNS` | felső korlát a körökre, vagy üres |
| `CIC_RESUME_SESSION` | folytatandó session azonosítója, vagy üres |
| `CIC_MCP_CONFIG` | MCP konfiguráció útvonala, vagy üres |
| `CIC_JOB_ID`, `CIC_WORKDIR` | tájékoztatásul |

Ami nem értelmezhető az adott agentre, azt a runner **hagyja figyelmen kívül**.
Egy MCP-t nem ismerő agent runnere ne hibázzon a `CIC_MCP_CONFIG` miatt.

## Kimenet — normalizált eredmény

A runner a `$CIC_RESULT_JSON`-ba írja, séma:
[`jobs/.schema/runner-result.schema.json`](../jobs/.schema/runner-result.schema.json).

```json
{
  "result": "az agent szöveges kimenete",
  "session_id": "folytatáshoz, ha az agent támogatja",
  "cost_usd": 0.42,
  "turns": 17,
  "stop_reason": "end_turn",
  "duration_ms": 123456,
  "models": "modell-a,modell-b",
  "tokens": { "input": 0, "output": 0, "cache_read": 0, "cache_creation": 0 }
}
```

**Csak a `result` kötelező.** Amit egy agent nem tud megmondani, az maradjon ki
— a factory üresen hagyja a `meta.yaml` megfelelő mezőjét. **Nullát írni oda,
ahol nincs adat, tilos:** a hamis nulla mérésnek látszik, a hiányzó mező nem.

## Exit kód

Az agent exit kódja. A `0` azt jelenti, hogy **az agent befejezte** — nem azt,
hogy a kimenet elfogadható. Azt a `close-job.sh` dönti el, output-kapu és review
után.

---

## Miért fájlban a prompt és miért JSON a kimenet

A prompt fájlban van, mert argumentumként a hossza platformfüggő korlátba ütközik.

A kimenet azért JSON és nem szabad szöveg, mert a `meta.yaml` `usage` blokkja
ebből áll elő, és azon mérjük a modell-rétegzés hatását. Egy runner, ami nem tud
költséget mondani, hagyja ki a mezőt — de amit mond, az legyen gépileg olvasható.

## Ha az agent nem ad értelmezhető JSON-t

A runner dolga, hogy akkor is érvényes eredményt írjon: a nyers kimenet a
`result`-ba, a többi mező kihagyva. A `run-job.sh` ezt `RUN_JSON_OK=0`-ként
kezeli, a jobot nem bukatja el emiatt, és a nyers szöveget megőrzi az embernek.

---

## Referencia-implementációk

| runner | mit futtat |
|---|---|
| [`tools/runners/claude.sh`](../tools/runners/claude.sh) | Claude Code (`claude --print --output-format json`) |
| [`tools/runners/echo.sh`](../tools/runners/echo.sh) | semmit — a promptot adja vissza. Ez teszi tesztelhetővé a teljes lifecycle-t agent, hálózat és költség nélkül |

Az `echo.sh` nem játék: ez az egyetlen módja annak, hogy a factory végigfuttatása
tesztelhető legyen. A `test-run-job-e2e.sh` ezt használja.
