# Beágyazási stratégia — mérve, nem becsülve (Task D)

## A mérés módszere

A build-time regiszter (Task B, 685 class-A erőforrás) és a `go:embed`-elt
guest-séma két külön réteg (a job spec D pontja szerint). A kérdés: mekkora
lenne a WASM bináris, ha a **teljes** class-A felületet a jelenlegi
beágyazási móddal (`//go:embed` + `[][]byte` lista) beágyaznánk?

Ezt **ténylegesen megépítettem és lemértem**, nem becsültem:

1. A `oci-sweep -write-schemas` a 685 class-A erőforrás `{config, state}`
   séma-bundle-jét kiírta lemezre (`docker compose exec builder`, konténeren
   belül, `/tmp/sweep-schemas/`).
2. A `module/` egy **eldobható másolatában** (`/tmp/module-scratch`, **nem**
   a repóban) kicseréltem a `contracts.go` két névre szóló
   `//go:embed schemas/core/vcn.json` / `.../subnet.json` párját egy
   `//go:embed schemas/full` könyvtár-embedre (`embed.FS`), és a 685
   sémafájlt bemásoltam oda.
3. `tinygo build -o /tmp/module-full.wasm -target wasip1 -scheduler=none .`
   — sikeresen lefordult.
4. Lemértem a bináris méretét, és összevetettem az **ugyanabban a
   konténerben, ugyanazzal a toolchainnel** frissen épített 2-erőforrásos
   (`vcn`+`subnet`) alappal — nem a committolt fájllal, hogy a toolchain
   ne legyen változó a mérésben.
5. A scratch-et töröltem (`/tmp` alól, nem a repóban) — a repóba **nem**
   került be a 685-erőforrásos beágyazás, csak a mérési eredmény.

## A számok

| Mennyiség | Érték |
|---|---:|
| nyers séma JSON, teljes felület (685 class-A erőforrás) | 4 835 490 byte (4,84 MB) |
| nyers séma JSON, jelenlegi alap (vcn+subnet) | 20 836 byte |
| `module.wasm`, teljes felület (685 erőforrás beágyazva) | 6 334 147 byte (6,04 MiB) |
| `module.wasm`, alap (2 erőforrás, ugyanaz a build) | 1 152 869 byte |
| delta (wasm) | 5 181 278 byte |
| delta (nyers JSON) | 4 814 654 byte |
| beágyazási többlet aránya (delta wasm / delta raw) | **1,076** — kb. 7,6% felül a nyers byte-on |
| átlag wasm-byte/erőforrás | ~7564 byte |
| relay alapértelmezett `MaxWASMModuleSize` | 16 777 216 byte (16 MiB, `CIC-Relay/cmd/relay/main_test.go:84`) |
| teljes felület a limit %-ában | **37,8%** |
| szabad hely a limit alatt | 10 443 069 byte (9,96 MiB) |

**A teljes OCI class-A felület (685 erőforrás) is beleférne a relay
alapértelmezett 16 MiB-os korlátjába** — 6,04 MiB, 62%-nyi tartalékkal. A
beágyazás byte-aránya közel lineáris (~1,08×) — a `go:embed` gyakorlatilag a
nyers byte-okat viszi be, a `embed.FS` könyvtár-index overhead-je kicsi.

Ebből extrapolálva: ~2065 erőforrás beágyazása fogyasztaná el a teljes 16
MiB-ot a jelenlegi alappal — ez majdnem a teljes SDK class-A+B osztálya
(685+621=1306) együtt, tehát **még egy "mindent egy binárisba" stratégia is
csak akkor ütközne a korláttal, ha a modul minden szolgáltatást importálna
egyszerre**, amit a pipeline-spec réges-rég kizár ("Split, don't monolith",
`docs/design/specs/oci-schema-pipeline.md`).

## A javaslat

**Nem "mert belefér" alapon mindent beágyazni.** A korlát alatt maradás nem
ok arra, hogy egy modul olyan szolgáltatások sémáit is behúzza, amiket sosem
importál — a sandbox-modell explicit, szűk deklarált felületet akar, nem
"amennyi belefér":

1. **Maradjon szelektív a beágyazás**, szolgáltatásonként/PoC-készletenként —
   a referenciamodul ma `core`/network-öt (vcn+subnet) ágyazza be, a
   roadmap P3.5 bővíti (RouteTable, SecurityList, NSG, gateway-ek), de
   *soha* nem a teljes SDK-t egy binárisba.
2. **A jelenlegi beágyazási mechanizmus (`vcnSchemaJSON`/`subnetSchemaJSON`
   két külön `//go:embed` sor + kézzel bővített `[][]byte` lista) nem
   skálázik** karbantartás szempontjából — minden új erőforráshoz kézzel kell
   sort írni a `contracts.go`-ba. A méréshez épített `//go:embed
   schemas/<service>` könyvtár-embed (egy sor, `embed.FS`, a
   `resourceContracts()` bejárja a könyvtárat) **működik és egyszerűbb** —
   ezt érdemes átvenni **függetlenül** a teljes/szelektív döntéstől, egy
   következő P2.3/P3.x jobban. Ez ebben a jobban **nem** került be a repóba
   (a `contracts.go`-n csak a `schemas/core/` path-váltás ment át, ami a
   Task C-hez kellett) — a méréshez a scratch-másolaton próbáltam ki, de a
   committolt kódot nem alakítottam át emiatt, mert az DoD 2 (a committolt
   `vcn`/`subnet` felület ne változzon) hatáskörén túlmutat egy önálló
   refaktor.
3. **Ha egy jövőbeli modul mégis sok tucat/száz erőforrást akarna egy
   binárisba ágyazni** (pl. egy "teljes network" build, nem csak PoC), a fenti
   ~7,6 KB/erőforrás arányból előre becsülhető a végméret — nincs szükség
   relay-oldali változásra, amíg egy modul a saját, deklarált szolgáltatás-
   körén belül marad.

## Relay-igény

**Nincs.** A mérés nem talált relay-oldali akadályt — a teljes felület is
belefér a jelenlegi alapértelmezett korlátba. Ha egy jövőbeli modul
ténylegesen 2000+ erőforrást akarna egy binárisba ágyazni, az a
`max_wasm_module_size` konfiggal (`CIC-Relay/cmd/relay/main.go:94`) már ma
is kezelhető az üzemeltető oldalán — ehhez sem kell relay-kód-változás.
