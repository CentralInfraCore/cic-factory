# #163 — `actuate` redirect / méretkorlát / policy parity a Rust `http-executor`-ral

Alap: `CIC_Relay` `main@852594a`. Ág: `feature/relay-163-actuate-egress`, helyi commit `54ef993` (pusholva, PR: https://github.com/CentralInfraCore/CIC_Relay/pull/180, base `main`).

## Mit találtam a kódban (állítás-ellenőrzés az issue szövegével szemben)

- **Igaz:** a `makeActuateFn` (`cmd/relay/cic_flow_host_funcs.go`) csak a kezdő URL-t veti össze az engedélylistával, aztán `deps.doer.Do`-val küld; a `newCICFlowRegistry` nil `doer`-t `http.DefaultClient`-re cserélt (redirectet követ, a környezeti proxyt használja, nincs időkorlát); a választ `io.ReadAll(resp.Body)` olvasta korlát nélkül.
- **Az issue "nem ellenőrzött" pontja eldőlt:** az éles bekötés **nil `doer`-t ad át** (`cmd/relay/main.go:664` `newCICFlowRegistry(buildOCIKeyResolver(), nil)`), tehát az éles út tényleg a `http.DefaultClient` volt, nem csak a teszt.
- **Igaz:** a Rust `http-executor` mind az öt védelmet alkalmazza: `redirect::Policy::none()`, `no_proxy()`, időkorlátok (30 s / 10 s), 1 MiB válaszplafon, SSRF-őr (DNS-feloldó szűri a tiltott tartományokat).
- **Az issue 3. pontja ("ugyanaz-e a policy") eltérést talált, amit nem a fixture old meg:** a Rust production policy csak `https`-t enged; a Go út `http`-t is, ha a modul manifestje megengedi. Ez manifest-szintű döntés, nem változtattam.
- **A meglévő `TestNewCICFlowRegistry_DefaultsDoer` a nem biztonságos alapértelmezést rögzítette** (`assert.Equal(http.DefaultClient, reg.doer)`); a javítással frissítettem.

## Mi változott

- `newEgressClient` (`cmd/relay/egress_client.go`): nincs redirect-követés (a 3xx a hívóhoz jut), a proxy-környezet figyelmen kívül marad, connect/kérés időkorlát (10 s / 30 s), és **minden kapcsolat dial-időben** a Rust-tal azonos tiltott tartományok ellen ellenőrzött (privát, loopback, link-local, unspecified, broadcast; IPv4-mapped kicsomagolva). Ez a DNS-válasz privát címre mutatását is fedi. Nil `doer` mostantól ezt kapja.
- Válaszplafon 1 MiB, **tipizált hiba** `{"error":…, "code":"response_too_large"}`; a deklarált hossz előre, az olvasás plafon+1 bájtnál megáll, tehát a nagy válasz nem kerül memóriába. A plafon bármely injektált `doer`-re is érvényes. A tiltott cím `code":"blocked_address"`.
- **Megosztott fixture** `testdata/egress-parity/policy.txt`: a három limit és 25 cím-ítélet (blocked/allowed). Go oldalon `TestEgressParity_Fixture`, Rust oldalon `egress_parity_fixture_matches_policy` (`http-executor/src/lib.rs`) olvassa; bármelyik oldal elmozdulása bukik. A fixture szándékosan sima szöveg, hogy a Rust crate ne kapjon új függőséget.

## Hívási út (production, `file:line`)

`cmd/relay/main.go:664` `newCICFlowRegistry(…, nil)` → `cic_flow_registry.go` `newEgressClient(false)` → `cmd/relay/cic_flow_host_funcs.go` `makeActuateFn` (`perModule(reg, makeActuateFn)`, `:85`) → `deps.doer.Do` → válaszplafon. `deadcode ./...`: nincs találat az új függvényekre.

## "Javítás nélkül bukik" bizonyíték

A régi viselkedés emulálva (`http.DefaultClient`-szerű kliens rövid időkorláttal, hogy a link-local cél ne akassza a futást; korlátlan `io.ReadAll`; scratchpad `163-without-fix-summary.txt`). Bukik: `TestActuate_RedirectToNonAllowedHost_NotFollowed` (mind a 3 alteszt: loopback másik port, link-local metadata, idegen host), `TestActuate_ResponseOverCap_TypedError` (mind a 3), `TestEgressClient_DialGuard_BlocksLoopback`, `TestEgressClient_IgnoresProxyEnvironment`, `TestEgressClient_DialGuard_MalformedAddressNotDialed`, `TestNewCICFlowRegistry_DefaultsDoer`. **Nem bukik** (karakterizáló / a függvényt fedi): `TestEgressParity_Fixture` a régi kliensen (az `isBlockedIP` változatlan) és `TestActuate_ResponseAtCap_NotRefused` (a határ-eset a régi kódon is átmegy). A fixture **mutáció** mindkét oldalon bukik (limit módosítva + `169.254.169.254` átbillentve: Go és Rust egyaránt FAIL).

A saját tesztjeimben az emuláció feltárt egy hibát: bukáskor típus-assertion-pánik nyelte el a többi eredményt; az assertionök védettek lettek.

## Helyi kapuk

Go (Docker `golang:1.26.11`): `gofmt -s -l` üres, `go vet ./...` üres, `staticcheck ./cmd/relay/` rc=0, `go test -count=1 ./...` minden csomag `ok`, `go test -race ./cmd/relay/` ok, `symbolsgen` után a `SYMBOLS.md` változatlan (nincs új exportált szimbólum), `MANIFEST.sha256` "no drift".
Rust (Docker `rust:1`, `--no-default-features`): `cargo test -p http-executor --locked --lib` 29/29 ok (köztük az új), `cargo fmt --check` ok, `cargo clippy --all-targets -D warnings` tiszta.

## Nyitott kérdések / jelzések

- **Viselkedésváltozás:** az alapértelmezett kliens nem tárcsáz privát/loopback/link-local címet. Egy modul, amelynek a manifestje belső hostot enged, mostantól `blocked_address` hibát kap. A repóban ilyet nem kerestem végig; éles manifestek átnézése a tulajdonosé. Tesztben a kliens `allowPrivate=true`-val épül (a Rust `insecure_allowing` megfelelője), éles úton nincs ilyen kapcsoló.
- **A parity részleges:** a limitek és a cím-ítéletek közösek (fixture). A "nincs redirect" mindkét oldalon külön tesztelt (Go: viselkedés-teszt; Rust: a kliens-építésben `Policy::none()`, ezt a fixture nem fedi). A Rust `https`-only policy és a Go manifest-szintű séma-döntés eltér.
- **Nem tükröztem:** a Rust `max_request_bytes` (kérés-plafon); az issue nem kéri.
- **Nem futtattam:** Rust `rustls` default feature-rel, `coverage-rust` és `deny-rust` kapu (csak a `--no-default-features` lib és a fmt/clippy). A `main()` nem futott.
- Kapcsolódik: #89.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Az éles `actuate` út `http.DefaultClient`-et használt | verified | `main.go:664` nil `doer`; régi `cic_flow_registry.go` nil → `http.DefaultClient`; a régi `TestNewCICFlowRegistry_DefaultsDoer` ezt rögzítette | Kódolvasás | alacsony |
| A redirect célja nincs újraellenőrizve | verified | A javítás nélküli emulációban `TestActuate_RedirectToNonAllowedHost_NotFollowed` mind a 3 esetben bukik | A régi viselkedéssel futtatott teszt | alacsony |
| A válaszolvasás korlátlan volt | verified | Régi `io.ReadAll(resp.Body)`; `TestActuate_ResponseOverCap_TypedError` javítás nélkül bukik (chunked: ~64 MiB leolvasva) | Kódolvasás + teszt | alacsony |
| A válaszplafon határ-eset helyes (pont a plafon átmegy, +1 bájt hiba) | verified | `TestActuate_ResponseAtCap_NotRefused`, `..._one_byte_over,_injected_doer` | Teszt | közepes: az at-cap teszt a régi kódon is zöld (határt nem véd, csak rögzít) |
| A kliens nem követ redirectet és nem használ proxyt | verified | `TestActuate_Redirect…` + `TestEgressClient_IgnoresProxyEnvironment` (a Transport.Proxy nil) | Teszt (a loopback-ot a Go amúgy sem proxyzza, ezért a Transportot állítom) | alacsony |
| A tiltott cím dial-időben elutasított (DNS-válasz is) | verified (loopback) | `TestEgressClient_DialGuard_BlocksLoopback`; `Control` a feloldás után fut | Teszt loopback célra; valódi DNS-feloldás nem tesztelt | közepes |
| A Go és a Rust ugyanazt az ítéletet adja a fixture-re | verified | `TestEgressParity_Fixture` + `egress_parity_fixture_matches_policy`; a mutált fixture mindkét oldalon bukik | Teszt mindkét nyelven | közepes: csak a cím-ítélet és a limitek közösek |
| Ugyanaz a séma-policy (https-only) a két oldalon | **cáfolt** | Rust production policy csak https; a Go út a manifest szerint http-t is enged | Kódolvasás | közepes |
| Az éles manifestek nem hivatkoznak privát hostra | **nem igazolt** | Nem néztem át az éles manifesteket | — | magas |
| A PR nyitva van | verified | https://github.com/CentralInfraCore/CIC_Relay/pull/180 | `gh pr create` kimenet | alacsony |
