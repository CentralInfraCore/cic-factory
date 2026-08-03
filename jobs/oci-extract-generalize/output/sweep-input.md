# Bemenet az `oci-extract-full-sweep` jobnak

Ez **nem** a sweep elvégzése. Ez az, amit a sweep tervezéséhez a felület alakjáról
megtudtam — hogy a következő job ne ugyanazokat a méréseket futtassa újra.

Minden szám a pinelt `v65.121.0` SDK-ra vonatkozik (`oci-sdk.lock.yaml`),
171 szolgáltatás, 319 kliensfájl.

---

## 1. Ami már nem kockázat

A műveleti extrakció **nem** szolgáltatás-specifikus, és ez mérve van:

```
TOTAL 8048/8048 operations resolved, 0 missing method/path
```

A sweep tehát **nem** fog method/path hiányba futni. Ha mégis, az SDK-bump
történt, nem resolver-hiba — és `make oci.audit` (exit 4) azonnal megmutatja.

Szintén stabilnak bizonyult az egész SDK-n: a publikus↔privát metódus-párosítás
(0 árva privát wire-metódus), a struct-tag szerződés, és a kliens-plumbing
elkülönítése.

---

## 2. Osztályozás — a sweep ezekbe a dobozokba fog esni

Az erőforrások a **create-felület** szerint osztályozódnak. Ez a
`Get<X>` műveletekből származtatott 1481 erőforrás-jelöltre mérve:

| Osztály | Darab | Mit jelent a sweepnek |
|---|---:|---|
| **A. Van read-modell és struct create-modell** | 639 | Mechanikus. A mai pipeline elbírja. Ez a sweep gerince |
| **B. Van read-modell, nincs `Create<R>Details`** | 570 | **Meg kell nézni, miért.** Két nagyon eltérő alcsoport — lásd lent |
| **C. Nincs read-modell a `Get<X>`-hez** | 264 | Nem erőforrás a mi értelmünkben (lista-, riport-, státusz-végpontok). **Indokolt kizárás**, de a kizárást fel kell írni, nem elhallgatni |
| **D. Polimorf (interface) create-modell** | 8 | Ma `exit 5`-tel jelentve. **Ne generálj rá sémát**, amíg a diszkriminátor-kezelés nincs eldöntve |

### A B osztály szétbontása — ezt a sweep ne keverje össze

A 570-ből a **túlnyomó többség jogosan nem hozható létre**: `WorkRequest`,
`Trace`, `Span`, `Log`, `Announcement`, `MonitorResult` — ezek olvasható
melléktermékek, nem provisionálható erőforrások. Ezeknek **nincs** create
operációjuk sem, tehát a strukturális resolver `CreateOp == nil`-t ad, és a
`Resolution.Unresolved` üres marad (nem hiba: nincs mit feloldani).

A valódi eset — van create művelet, csak nem „Create" a neve — **ritka**. Az
általam mért, megbízható jel az alternatív *létrehozó* igére:

| Ige | Eset | Példa |
|---|---:|---|
| `Launch` | 3 | `core:LaunchInstance`, `database:LaunchDbSystem`, `database:LaunchAutonomousExadataInfrastructure` |
| `Put` | 1 | `objectstorage:PutObjectLifecyclePolicy` |

**Fontos figyelmeztetés a mérésemből:** ha „bármely `<Ige><R>` + `<Ige><R>Details`
párra" keresel, ~90 igét fogsz kapni (`Approve`, `Reject`, `Download`, `Reboot`,
`Failover`…) — ezek **akciók**, nem create-ek. Az ige-alapú keresés zajos.
**Ezért nem ige-alapú a resolver:** a `POST <collection>` szabály a hármat
megtalálja, a kilencvenet nem, mert azok nem a kollekciós úton POST-olnak.
A sweep se ige-listát építsen.

---

## 3. Ahol további törés várható — prioritási sorrendben

### 3.1 Címzés (a legnagyobb tétel)

**323 / 1481 `Get*` művelet (21,8%), 65 / 158 szolgáltatásban** nem egy
path-paraméterrel címez:

```
0 params:   50      (singleton erőforrás: nincs kollekciós út → CreateOp nem lesz)
1 params: 1108      (a mai bevált eset)
2 params:  265
3 params:   48
4 params:    9
5 params:    1      (datacatalog:GetAttributeTag)
```

Az extractor most már **kiadja** a `path_params` listát minden műveletnél. Amit a
sweep előtt el kell dönteni:

- **Honnan jön a nem-id path-paraméter értéke?** A `namespaceName` a bindingből?
  A config sémából? Egy új `x-cic-addressing` blokkból? Ez **beágyazási döntés**,
  amit ez a job szándékosan nem hozott meg.
- **`module/provider.go:1059` `templatePath` ma minden `{…}`-ba a resource id-t
  írja.** Egy path-paraméternél helyes, kettőnél szemetet ad. Ez a modul futásidejű
  oldala — a sweep előtt vagy vele együtt javítandó, különben a többparaméteres
  erőforrásokra generált séma használhatatlan lesz.
- A **0 paraméteres** (singleton) eset saját szabályt igényel: nincs kollekciós
  út, tehát a mai `create = POST <collection>` nem talál semmit. 50 művelet.

### 3.2 Polimorfizmus

1014 interface-modell, ebből 470 `*Details`/`*Base`. Ma jelentve, nem kibontva.
A sweep előtt eldöntendő: a `x-cic-go-type` flag elég-e, vagy a diszkriminátoros
`oneOf` kibontás kell. Ez **séma-modellezési** kérdés, nem extrakciós.

### 3.3 A bemeneti fájllista kézi kurálása — még nyitott

Ez a job **nem** oldotta meg, és fel kell írni: a `make oci.generate` ma
erőforrásonként **kézzel felsorolt** fájllistát ad az extractornak:

```
create_vcn_details.go update_vcn_details.go vcn.go change_vcn_compartment_details.go <client>
```

Ez maga egy erőforrás-specifikus feltételezés: az operátornak tudnia kell, mely
akciómodell-fájlok tartoznak az erőforráshoz. Konkrét következménye **ma is
mérhető**: a VCN-nek hat akciója van (`AddVcnCidr`, `RemoveVcnCidr`,
`ModifyVcnCidr`, `AddIpv6VcnCidr`, `RemoveIpv6VcnCidr`, `ChangeVcnCompartment`),
de csak a `change_vcn_compartment_details.go` van felsorolva — ezért a `cidrBlock`
a committolt `vcn.json`-ban **`create-only`**, holott valójában
`AddVcnCidr`/`RemoveVcnCidr` akción keresztül változtatható.

**Miért nem javítottam itt:** a fájllista automatikus származtatása megváltoztatná
a `vcn`/`subnet` committolt felületét (a DoD 2 tiltja), és felvetne egy
modellezési kérdést, ami nem az enyém: a `ModifyVcnCidrDetails` mezői
(`originalCidrBlock`, `newCidrBlock`) **akció-argumentumok**, nem erőforrás-mezők
— nem nyilvánvaló, hogy a config sémába valók-e egyáltalán. Ez pontosan a job
által a sweepre utalt „kapu-granularitás / beágyazási stratégia".

**Javaslat a sweepnek:** a resolver már megtalálja az akció-*műveleteket*
path-alapon; elég lenne a modell-fájlokat a szolgáltatás könyvtárából
származtatni. De előbb dönteni kell az akció-argumentumok helyéről.

---

## 4. Mit érdemes indokolt kizárásként kezelni

Ezeket **nevesítve** zárja ki a sweep, ne csak hallgasson róluk:

- **3 `*_client.go` fájl 0 művelettel:** `common/auth/federation_client.go`,
  `database_tools_connection_oracle_database_proxy_client.go`,
  `cloud_gate_oauth_client.go` — nem szolgáltatás-kliensek.
- **A C osztály (264 erőforrás read-modell nélkül)** — `Get<X>`, ahol nincs `X`
  struct: riport/státusz végpontok.
- **`WorkRequest` és rokonai** — olvasható melléktermékek. Megjegyzés: a modulnak
  van `poll` művelete work-requestre (`module/provider.go`), tehát a
  work-request-*olvasás* kell, de nem provisionálható erőforrásként.
- **A D osztály (8 polimorf create)** — amíg a 3.2 döntés nincs meg.

---

## 5. Mérőeszközök, amiket örökölsz

Ne írd újra őket:

| Eszköz | Mit ad |
|---|---|
| `oci-extract -audit <client.go>…` | jelöltek/feloldottak külön számolva, exit 4 ha bármi feloldatlan |
| `make oci.audit` | ugyanez az egész pinelt SDK-n (hálózat kell, nem CI-kapu) |
| `oci-extract -schema/-policy` | stderr-re jelenti a feloldatlan felületet, **exit 5** |
| `oci-extract -diff <old> <new>` | P2.4 szemantikus gate, exit 3 breakingre |
| `tools/oci-extract/regression_test.go` | a `vcn`+`subnet` felület befagyasztva, offline fut |
| `Resolution.ReadOpSource` | megmondja, strukturálisan vagy névkonvencióval oldott-e fel |

**Egy dolgot tarts meg elvként:** a régi extractor hibamintája a *némaság* volt —
kihagyta, amit nem tudott feloldani, és a kimenet érvényesnek látszott. A sweep
során minden új kihagyás legyen szám vagy exit kód, ne hiányzó sor.
