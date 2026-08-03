# Szolgáltatásonkénti lefedettség (Task B)

## Az eszköz

A sweep nem kézzel válogatott séma-listát ad, hanem egy új build-time tool-t:
[`tools/oci-extract/cmd/oci-sweep`](../../../../cic-module-oracle-cloud/tools/oci-extract/cmd/oci-sweep/main.go)
(a modul-repóban, `feature/oci-extract-full-sweep` ágon). Szolgáltatásonként
(az SDK top-level könyvtárai) lefuttatja a már meglévő, P2.2/P2.5-ben
bevált gépezetet (`AuditClientFile`, `ExtractClientFile`, `ExtractFile`,
`Resolve`) — nem ír új feloldási logikát, csak skálázza a meglévőt az egész
pinelt SDK-ra.

Reprodukálás (a modul-repo klónjában, a builder konténerben):

```sh
export GOPATH=/tmp/ocigp GOMODCACHE=/tmp/ocigp/pkg/mod GOFLAGS=-mod=mod
SDK=/tmp/ocigp/pkg/mod/github.com/oracle/oci-go-sdk/v65@v65.121.0
go mod download github.com/oracle/oci-go-sdk/v65@v65.121.0
cd tools/oci-extract && go run ./cmd/oci-sweep -sdk "$SDK" -write-schemas /tmp/sweep-schemas
```

## 1 — Művelet-feloldás (DoD 2, azonos alakban mint P2.2 VCN 271/271)

```
TOTAL 8048/8048 operations resolved, 0 missing method/path
```

Ez **nem változott** a P2.5-höz képest (ugyanaz a szám) — a sweep tool a
művelet-szintű feloldást csak *szolgáltatásonként* bontja fel, nem méri újra
más módszertannal. A `core` szolgáltatás (VCN + Compute + ComputeManagement +
BlockStorage 4 kliensfájlja együtt): **493/493**, ebből a VCN-kliens önmagában
a korábban igazolt **271/271**.

## 2 — Erőforrás-osztályozás a teljes SDK-n

A `sweep-input.md` (előző job) A/B/C/D osztályozását futtattam újra, de a
**jelenlegi, P2.5 utáni strukturális resolverrel** (nem a régi
név-konvenciós logikával, amire az előző job becslése épült — ezért térnek el
a számok az ottani 639/570/264/8-tól):

| Osztály | Darab | Definíció |
|---|---:|---|
| **A** | 685 | van read-modell ÉS feloldható create-művelet (`CreateOp != nil`) — a mai pipeline mechanikusan kezeli |
| **B** | 621 | van read-modell, de nincs feloldható create-felület (jellemzően jogos: `WorkRequest` és rokonai olvasható melléktermékek) |
| **C** | 62 | nincs read-modell a `Get<X>`-hez — riport/státusz végpont, nem erőforrás |
| **D** | 106 | polimorf create (83) és/vagy read (90) modell — jelentve, nem kibontva |

Összesen **1474 erőforrás-jelölt**, 168 szolgáltatásból (lásd 4. pont a
171-168 eltérésről).

**A B osztály mérete (621) nem risk-jel.** A resolver P2.5 óta *strukturális*
(HTTP-felület alapú), nem név-konvenciós — tehát a `Launch`/`Put` típusú,
nem-"Create"-nevű create-műveletek már a resolverben megtalálhatók, nem esnek
a B osztályba. Ami B-ben marad, az túlnyomórészt jogosan nem-létrehozható
melléktermék (work request, trace, span, log, announcement stb.) — ahogy az
előző job is jelezte, csak most már mérve, nem becsülve.

## 3 — Szolgáltatásonkénti tábla

```text
Service | Client files | Ops resolved | Resource candidates | A | B | C | D
```

| Service | Client files | Ops resolved | Resource candidates | A | B | C | D |
|---|---:|---:|---:|---:|---:|---:|---:|
| accessgovernancecp | 1 | 8/8 | 2 | 1 | 1 | 0 | 0 |
| adm | 1 | 37/37 | 6 | 4 | 1 | 0 | 1 |
| aidataplatform | 1 | 12/12 | 2 | 1 | 1 | 0 | 0 |
| aidocument | 1 | 27/27 | 5 | 3 | 2 | 0 | 0 |
| ailanguage | 1 | 44/44 | 6 | 4 | 2 | 0 | 0 |
| aispeech | 1 | 19/19 | 3 | 2 | 1 | 0 | 0 |
| aivision | 1 | 54/54 | 10 | 9 | 1 | 0 | 0 |
| analytics | 1 | 24/24 | 3 | 2 | 1 | 0 | 0 |
| announcementsservice | 4 | 19/19 | 5 | 2 | 3 | 0 | 0 |
| apiaccesscontrol | 4 | 21/21 | 4 | 2 | 2 | 0 | 0 |
| apigateway | 6 | 64/64 | 11 | 7 | 3 | 1 | 0 |
| apiplatform | 1 | 10/10 | 2 | 1 | 1 | 0 | 0 |
| apmconfig | 1 | 19/19 | 3 | 0 | 1 | 1 | 1 |
| apmcontrolplane | 1 | 14/14 | 2 | 1 | 1 | 0 | 0 |
| apmsynthetics | 1 | 28/28 | 6 | 5 | 1 | 0 | 0 |
| apmtraces | 4 | 20/20 | 7 | 1 | 6 | 0 | 0 |
| appmgmtcontrol | 1 | 8/8 | 2 | 0 | 2 | 0 | 0 |
| artifacts | 1 | 33/33 | 7 | 2 | 4 | 0 | 1 |
| audit | 1 | 3/3 | 1 | 0 | 1 | 0 | 0 |
| autoscaling | 1 | 11/11 | 2 | 1 | 0 | 0 | 1 |
| bastion | 1 | 15/15 | 3 | 2 | 1 | 0 | 0 |
| batch | 1 | 44/44 | 7 | 5 | 1 | 0 | 1 |
| bds | 1 | 97/97 | 12 | 9 | 2 | 0 | 1 |
| blockchain | 1 | 27/27 | 4 | 3 | 1 | 0 | 0 |
| budget | 2 | 26/26 | 5 | 4 | 1 | 0 | 0 |
| capacitymanagement | 3 | 57/57 | 9 | 6 | 2 | 1 | 0 |
| certificates | 1 | 5/5 | 3 | 0 | 2 | 0 | 1 |
| certificatesmanagement | 1 | 32/32 | 6 | 3 | 3 | 0 | 0 |
| cims | 1 | 7/7 | 1 | 1 | 0 | 0 | 0 |
| cloudbridge | 4 | 59/59 | 9 | 5 | 2 | 0 | 2 |
| cloudguard | 1 | 155/155 | 31 | 14 | 16 | 1 | 0 |
| cloudmigrations | 1 | 43/43 | 7 | 4 | 2 | 0 | 1 |
| clusterplacementgroups | 1 | 13/13 | 2 | 1 | 1 | 0 | 0 |
| computecloudatcustomer | 1 | 12/12 | 2 | 2 | 0 | 0 | 0 |
| computeinstanceagent | 3 | 9/9 | 3 | 1 | 2 | 0 | 0 |
| containerengine | 1 | 50/50 | 12 | 5 | 7 | 0 | 0 |
| containerinstances | 1 | 18/18 | 3 | 1 | 2 | 0 | 0 |
| containerregistry | 1 | 1/1 | 1 | 0 | 1 | 0 | 0 |
| **core** | 4 | **493/493** | 102 | 52 | 44 | 4 | 2 |
| costad | 1 | 16/16 | 3 | 2 | 1 | 0 | 0 |
| dashboardservice | 2 | 12/12 | 2 | 1 | 0 | 0 | 1 |
| database | 1 | 456/456 | 78 | 34 | 35 | 1 | 8 |
| databasemanagement | 5 | 341/341 | 75 | 14 | 57 | 0 | 4 |
| databasemigration | 1 | 69/69 | 11 | 1 | 5 | 2 | 3 |
| databasetools | 2 | 67/67 | 9 | 1 | 2 | 0 | 6 |
| databasetoolsruntime | 1 | 44/44 | 11 | 2 | 2 | 1 | 6 |
| datacatalog | 1 | 149/149 | 25 | 21 | 4 | 0 | 0 |
| datacc | 1 | 41/41 | 7 | 3 | 4 | 0 | 0 |
| dataflow | 1 | 45/45 | 8 | 6 | 1 | 1 | 0 |
| dataintegration | 1 | 163/163 | 39 | 22 | 11 | 0 | 6 |
| datalabelingservice | 1 | 17/17 | 2 | 1 | 1 | 0 | 0 |
| datalabelingservicedataplane | 1 | 15/15 | 5 | 2 | 1 | 2 | 0 |
| datasafe | 1 | 368/368 | 56 | 29 | 25 | 1 | 1 |
| datascience | 1 | 171/171 | 29 | 16 | 4 | 8 | 1 |
| dblm | 1 | 14/14 | 4 | 1 | 3 | 0 | 0 |
| dbmulticloud | 10 | 80/80 | 13 | 10 | 3 | 0 | 0 |
| delegateaccesscontrol | 2 | 30/30 | 7 | 2 | 5 | 0 | 0 |
| demandsignal | 2 | 12/12 | 2 | 2 | 0 | 0 | 0 |
| desktops | 1 | 21/21 | 3 | 1 | 2 | 0 | 0 |
| devops | 1 | 139/139 | 33 | 8 | 15 | 3 | 7 |
| dif | 1 | 13/13 | 2 | 1 | 1 | 0 | 0 |
| disasterrecovery | 1 | 36/36 | 5 | 4 | 1 | 0 | 0 |
| distributeddatabase | 4 | 57/57 | 6 | 3 | 3 | 0 | 0 |
| dns | 1 | 54/54 | 11 | 4 | 4 | 1 | 2 |
| email | 1 | 48/48 | 8 | 6 | 2 | 0 | 0 |
| emaildataplane | 1 | 2/2 | 0 | 0 | 0 | 0 | 0 |
| emwarehouse | 1 | 13/13 | 3 | 1 | 2 | 0 | 0 |
| events | 1 | 6/6 | 1 | 1 | 0 | 0 | 0 |
| filestorage | 1 | 74/74 | 10 | 7 | 2 | 0 | 1 |
| fleetappsmanagement | 8 | 149/149 | 26 | 16 | 10 | 0 | 0 |
| fleetsoftwareupdate | 1 | 52/52 | 10 | 2 | 1 | 2 | 5 |
| functions | 2 | 17/17 | 4 | 2 | 2 | 0 | 0 |
| fusionapps | 1 | 74/74 | 18 | 10 | 8 | 0 | 0 |
| gdp | 1 | 14/14 | 2 | 1 | 1 | 0 | 0 |
| generativeai | 1 | 90/90 | 16 | 14 | 2 | 0 | 0 |
| generativeaiagent | 1 | 44/44 | 9 | 7 | 1 | 1 | 0 |
| generativeaiagentruntime | 1 | 6/6 | 1 | 1 | 0 | 0 | 0 |
| generativeaidata | 5 | 5/5 | 1 | 0 | 1 | 0 | 0 |
| generativeaiinference | 1 | 7/7 | 0 | 0 | 0 | 0 | 0 |
| genericartifactscontent | 1 | 3/3 | 2 | 0 | 0 | 2 | 0 |
| goldengate | 1 | 96/96 | 10 | 5 | 3 | 0 | 2 |
| governancerulescontrolplane | 2 | 20/20 | 5 | 2 | 3 | 0 | 0 |
| healthchecks | 1 | 17/17 | 2 | 2 | 0 | 0 | 0 |
| identity | 1 | 145/145 | 21 | 12 | 8 | 0 | 1 |
| identitydataplane | 1 | 2/2 | 0 | 0 | 0 | 0 | 0 |
| identitydomains | 2 | 330/330 | 58 | 40 | 18 | 0 | 0 |
| integration | 1 | 23/23 | 2 | 1 | 1 | 0 | 0 |
| iot | 1 | 42/42 | 9 | 6 | 1 | 2 | 0 |
| jms | 1 | 91/91 | 14 | 4 | 10 | 0 | 0 |
| jmsjavadownloads | 1 | 25/25 | 6 | 3 | 2 | 1 | 0 |
| jmsutils | 1 | 18/18 | 5 | 0 | 5 | 0 | 0 |
| keymanagement | 5 | 63/63 | 10 | 5 | 5 | 0 | 0 |
| licensemanager | 1 | 18/18 | 5 | 2 | 3 | 0 | 0 |
| limits | 2 | 11/11 | 2 | 1 | 1 | 0 | 0 |
| limitsincrease | 1 | 11/11 | 2 | 1 | 1 | 0 | 0 |
| loadbalancer | 1 | 61/61 | 13 | 8 | 5 | 0 | 0 |
| lockbox | 1 | 24/24 | 6 | 3 | 3 | 0 | 0 |
| loganalytics | 1 | 200/200 | 40 | 6 | 33 | 0 | 1 |
| logging | 1 | 30/30 | 5 | 4 | 1 | 0 | 0 |
| loggingingestion | 1 | 1/1 | 0 | 0 | 0 | 0 | 0 |
| loggingsearch | 1 | 1/1 | 0 | 0 | 0 | 0 | 0 |
| lustrefilestorage | 1 | 26/26 | 4 | 2 | 2 | 0 | 0 |
| managedkafka | 1 | 29/29 | 5 | 2 | 2 | 0 | 1 |
| managementagent | 1 | 34/34 | 8 | 2 | 4 | 1 | 1 |
| managementdashboard | 1 | 18/18 | 4 | 2 | 2 | 0 | 0 |
| marketplace | 2 | 34/34 | 9 | 2 | 5 | 0 | 2 |
| marketplaceprivateoffer | 2 | 11/11 | 4 | 2 | 1 | 1 | 0 |
| marketplacepublisher | 1 | 85/85 | 19 | 3 | 8 | 4 | 4 |
| mediaservices | 2 | 62/62 | 8 | 5 | 1 | 0 | 2 |
| mngdmac | 2 | 14/14 | 3 | 1 | 2 | 0 | 0 |
| modeldeployment | 1 | 2/2 | 0 | 0 | 0 | 0 | 0 |
| monitoring | 1 | 18/18 | 3 | 2 | 1 | 0 | 0 |
| multicloud | 8 | 13/13 | 3 | 0 | 3 | 0 | 0 |
| mysql | 6 | 57/57 | 10 | 5 | 5 | 0 | 0 |
| networkfirewall | 1 | 93/93 | 16 | 8 | 2 | 0 | 6 |
| networkloadbalancer | 1 | 35/35 | 10 | 4 | 6 | 0 | 0 |
| nosql | 1 | 27/27 | 5 | 2 | 2 | 0 | 1 |
| objectstorage | 1 | 56/56 | 10 | 5 | 3 | 2 | 0 |
| oce | 1 | 10/10 | 2 | 1 | 1 | 0 | 0 |
| ocicontrolcenter | 1 | 3/3 | 0 | 0 | 0 | 0 | 0 |
| ocvp | 9 | 68/68 | 9 | 8 | 1 | 0 | 0 |
| oda | 3 | 83/83 | 15 | 9 | 3 | 0 | 3 |
| onesubscription | 8 | 13/13 | 3 | 0 | 3 | 0 | 0 |
| ons | 2 | 16/16 | 4 | 2 | 1 | 1 | 0 |
| opa | 1 | 13/13 | 2 | 1 | 1 | 0 | 0 |
| opensearch | 3 | 26/26 | 4 | 2 | 2 | 0 | 0 |
| operatoraccesscontrol | 4 | 26/26 | 6 | 2 | 4 | 0 | 0 |
| opsi | 1 | 198/198 | 20 | 8 | 4 | 2 | 6 |
| optimizer | 1 | 26/26 | 6 | 1 | 5 | 0 | 0 |
| osmanagementhub | 11 | 171/171 | 23 | 5 | 11 | 4 | 3 |
| ospgateway | 4 | 13/13 | 4 | 0 | 4 | 0 | 0 |
| osubbillingschedule | 1 | 1/1 | 0 | 0 | 0 | 0 | 0 |
| osuborganizationsubscription | 1 | 1/1 | 0 | 0 | 0 | 0 | 0 |
| osubsubscription | 3 | 4/4 | 1 | 0 | 1 | 0 | 0 |
| osubusage | 1 | 3/3 | 1 | 0 | 1 | 0 | 0 |
| psa | 1 | 12/12 | 2 | 1 | 1 | 0 | 0 |
| psql | 1 | 42/42 | 8 | 3 | 5 | 0 | 0 |
| queue | 2 | 24/24 | 5 | 2 | 3 | 0 | 0 |
| recovery | 1 | 26/26 | 4 | 3 | 1 | 0 | 0 |
| redis | 7 | 40/40 | 6 | 4 | 2 | 0 | 0 |
| resourceanalytics | 3 | 22/22 | 4 | 3 | 1 | 0 | 0 |
| resourcemanager | 1 | 52/52 | 17 | 4 | 3 | 9 | 1 |
| resourcescheduler | 1 | 14/14 | 2 | 1 | 1 | 0 | 0 |
| resourcesearch | 1 | 3/3 | 1 | 0 | 1 | 0 | 0 |
| rover | 6 | 43/43 | 8 | 3 | 5 | 0 | 0 |
| sch | 2 | 14/14 | 3 | 1 | 1 | 0 | 1 |
| secrets | 1 | 3/3 | 1 | 0 | 1 | 0 | 0 |
| securityattribute | 1 | 18/18 | 3 | 2 | 1 | 0 | 0 |
| self | 2 | 15/15 | 3 | 1 | 2 | 0 | 0 |
| servicecatalog | 1 | 28/28 | 8 | 3 | 2 | 2 | 1 |
| servicemanagerproxy | 1 | 2/2 | 1 | 0 | 1 | 0 | 0 |
| stackmonitoring | 1 | 87/87 | 12 | 10 | 1 | 0 | 1 |
| streaming | 2 | 30/30 | 6 | 3 | 3 | 0 | 0 |
| tenantmanagercontrolplane | 11 | 54/54 | 13 | 4 | 7 | 0 | 2 |
| threatintelligence | 1 | 5/5 | 1 | 0 | 1 | 0 | 0 |
| usage | 3 | 9/9 | 0 | 0 | 0 | 0 | 0 |
| usageapi | 1 | 33/33 | 6 | 5 | 1 | 0 | 0 |
| vault | 1 | 13/13 | 2 | 1 | 1 | 0 | 0 |
| vbsinst | 1 | 10/10 | 2 | 1 | 1 | 0 | 0 |
| visualbuilder | 1 | 14/14 | 2 | 1 | 1 | 0 | 0 |
| vnmonitoring | 1 | 12/12 | 2 | 1 | 1 | 0 | 0 |
| vulnerabilityscanning | 1 | 58/58 | 12 | 4 | 8 | 0 | 0 |
| waa | 2 | 17/17 | 3 | 1 | 1 | 0 | 1 |
| waas | 2 | 72/72 | 14 | 5 | 9 | 0 | 0 |
| waf | 1 | 24/24 | 4 | 1 | 1 | 0 | 2 |
| wlms | 2 | 43/43 | 10 | 0 | 9 | 0 | 1 |
| workrequests | 1 | 4/4 | 1 | 0 | 1 | 0 | 0 |
| zpr | 1 | 15/15 | 4 | 1 | 3 | 0 | 0 |

Minden sorban `Ops resolved` = X/X (nincs feloldatlan sorban maradt).

## 4 — Indokolt kizárások (nem csendes kihagyás)

**Miért 168 szolgáltatás, nem 171** (a P2.5-ös dokumentáció ezt a számot
használja a `make oci.audit` alapján): a 171-es szám a **kliensfájlok**
darabszáma szerint metsz máshol, mint az én "szolgáltatás = SDK top-level
könyvtár, amiben van legalább egy `*_client.go`" definícióm. A sweep 168
könyvtárat talált ilyen kritériummal — a különbség onnan jön, hogy
`common/auth/federation_client.go` **nem** egy top-level szolgáltatás-könyvtár
alatt van, hanem két szinttel lejjebb (`common/auth/`), tehát a
top-level-könyvtár bejárás nem látja szolgáltatásként. Ezt a fájlt külön,
explicit auditáltam (lásd lent) — a művelet-számba be van számítva (0
darab), csak a "szolgáltatás" darabszámba nem.

**3+1, névvel azonosított, 0-műveletes `*_client.go`** (a `sweep-input.md`
által előre jelzett lista, most tényleges elérési úttal):

| Fájl | Indoklás |
|---|---|
| `common/auth/federation_client.go` | token-exchange plumbing, nem szolgáltatás-kliens |
| `databasetools/database_tools_connection_oracle_database_proxy_client.go` | connection-proxy alias kliens, nincs saját művelete |
| `identitydomains/cloud_gate_oauth_client.go` | OAuth helper kliens, nincs provisioning-művelete |

(A `sweep-input.md` egy negyedik, `cloud_gate_oauth_client.go`-t is
`cloudgate`-nek címzett — a valós elérési út `identitydomains/`-on belül van,
ezt itt korrigáltam.)

**C osztály (62 db)** és **D osztály (106 db)**: kategorikusan kizárva a
sémagenerálásból (lásd 2. pont), de számmal, nem hallgatással — a teljes
lista `-write-schemas` nélkül is kinyerhető az eszközből (`class_c`-nek
nincs kimenő fájlja, mert nincs mit sémázni; `class_d`-nek szándékosan
nincs, amíg a diszkriminátor-kibontás nincs eldöntve).

## 5 — Amit ez a sweep NEM csinált

- **Nem bontotta ki a polimorf modelleket** (D osztály, 106 erőforrás) — ez
  külön modellezési döntés (`sweep-input.md` 3.2), nem ennek a jobnak a
  hatásköre.
- **Nem oldotta meg a bemeneti fájllista kézi kurálását** (`sweep-input.md`
  3.3, a VCN hat akciója közül csak egy van bekötve) — ez a `make
  oci.generate` Makefile-célját érintené, amit ez a job szándékosan nem
  módosított (a DoD 2 tiltja a committolt `vcn`/`subnet` felület
  megváltoztatását, és a sweep tool a *build-time regisztert* bővíti, nem az
  *embedelt* célokat — lásd `embedding-strategy.md`).
