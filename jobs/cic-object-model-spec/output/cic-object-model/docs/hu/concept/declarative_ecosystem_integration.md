# Tervrajz: A Deklaratív, Kétsebességes Ökoszisztéma

## 1. Filozófia és Alapelvek

A CIC projekt nem egy monolitikus szoftver, hanem független, de szorosan összetartozó komponensek dinamikus ökoszisztémája. Egy ilyen elosztott rendszer fejlesztése és integrációja során a hagyományos modellek (tiszta monorepo vagy tiszta multi-repo) korlátokba ütköznek. Ezért egy hibrid, a modern Platform Engineering elveire épülő stratégiát alkalmazunk.

A rendszerünk központi filozófiája nem a hibák erőszakos megakadályozása, hanem a **maximális transzparencia és a villámgyors, automatizált diagnosztika** biztosítása. A rendszer nem "öngyógyító", hanem **"öndiagnosztizáló"**. A felelősséget nem veszi le a fejlesztői csapatokról, hanem egyértelmű, vitathatatlan, valós idejű adatokat ad a kezükbe a helyes döntések meghozatalához.

### Alapelveink

*   **Deklaratív Ökoszisztéma:** A komponensek közötti kapcsolatot nem a kódban vagy a fejlesztők fejében rejtjük el, hanem egy központi, verziókezelt konfigurációs fájlban **deklaráljuk**. Ez a konfiguráció a rendszer élő, lélegző "térképe".
*   **Kétsebességes Kockázatkezelés:** Párhuzamosan működtetünk egy "gyors" (commit-szintű) és egy "lassú" (release-szintű) integrációs folyamatot. Ezzel a kettős megközelítéssel egyszerre biztosítjuk a maximális fejlesztési sebességet és az éles rendszer sziklaszilárd stabilitását.
*   **Automatizált Visszacsatolás:** Minden, a rendszerben történő változás egy automatizált kaszkádot indít el, ami a teljes ökoszisztémán végigfuttatja a szükséges teszteket. Az eredményeket egy központi helyen, egy "irányítópulton" jeleníti meg, azonnali és egyértelmű visszacsatolást adva a változás hatásairól.

---

## 2. A Rendszer Anatómája: Kulcskomponensek

A gépezet öt fő építőelemre támaszkodik:

*   **Szülő Repó (Parent Repo):** Egy központi, "ős" repository, ami egy logikai egység (pl. egy közös alap, egy platform-komponens) fejlesztését tartalmazza. Ez a repó a változások forrása.

*   **Gyermek Repó (Child Repo):** Egy olyan repository, ami függ a Szülő Repótól. Ez a repó a változások "fogyasztója".

*   **Ökoszisztéma Térkép (`ecosystem.yaml`):** A Szülő Repóban található, verziókezelt fájl. A `children` mező alatt explicit módon listázza az összes tőle függő Gyermek Repó azonosítóját. Ez a rendszer DNS-e, a központi igazságforrás a függőségi gráfról.

*   **Renovate Konfiguráció (`renovate.json`):** A Gyermek Repókban található fájl, ami leírja a Renovate bot viselkedését, azaz hogy *hogyan* kell a szülőtől érkező frissítéseket kezelnie (pl. milyen néven hozzon létre ágat, milyen commit üzenetet használjon).

*   **CI/CD Orchestrator:** A Szülő Repó CI/CD pipeline-ja, ami a "karmester" szerepét tölti be. Ő olvassa be a Térképet, és indítja el a kaszkádot a Gyermek Repók felé, amikor a Szülőben változás történik.

---

## 3. A Gépezet Működése: A Két Vérkeringés

A rendszer két, párhuzamosan futó, de eltérő célú "vérkeringést" működtet a változások kezelésére.

### 3.1. A Gyors Vérkeringés (Fejlesztési Folyamat)

*   **Cél:** Azonnali visszacsatolás. Annak biztosítása, hogy a Szülő Repó legfrissebb, fejlesztés alatt álló változásai ne törjék el a tőle függő komponenseket. A hibákat a keletkezésük pillanatában akarjuk elkapni, nem napokkal később.

*   **Folyamat:**
    1.  **Trigger:** Egy fejlesztő commit-ot push-ol a `Szülő Repó` `main` (vagy `dev`) ágára.
    2.  **Orchestráció:** A `Szülő Repó` CI pipeline-ja (az Orchestrator) elindul. Beolvassa az `ecosystem.yaml`-t, és minden `children` listában szereplő repóhoz kiküld egy `repository_dispatch` eseményt. Az esemény payload-ja tartalmazza a Szülő Repó új **commit hash**-ét.
    3.  **Integráció:** A `Gyermek Repó` egy dedikált, erre a célra létrehozott CI pipeline-ja elindul az esemény hatására. A kapott commit hash alapján létrehoz egy ideiglenes, `r/parent-integration/<commit_hash>` nevű ágat, és megpróbálja beolvasztani a szülő változását.
    4.  **Tesztelés:** A `Gyermek Repó` lefuttatja a saját, teljes tesztkészletét ezen az ideiglenes, integrációs ágon.
    5.  **Visszacsatolás:** A tesztelés eredményétől függően a `Gyermek Repó` CI-ja egy státusz-ellenőrzést (`success` vagy `failure`) küld vissza a GitHub API-n keresztül a `Szülő Repó` eredeti commitjához.

*   **Eredmény:** A `Szülő Repó` commit-history-jában minden egyes commit mellett egyértelműen láthatóvá válik, hogy az a teljes ökoszisztémában sikeresen integrálható-e. A fejlesztők azonnali, célzott visszajelzést kapnak a változtatásuk hatásairól.

### 3.2. A Lassú Vérkeringés (Stabil Release Folyamat)

*   **Cél:** Az éles rendszer stabilitásának garantálása. Annak biztosítása, hogy a Gyermek Repók `main` ágába csak a Szülő Repó hivatalos, letesztelt, stabil kiadásai kerülhessenek be, egy kontrollált és auditálható folyamaton keresztül.

*   **Folyamat:**
    1.  **Trigger:** A `Szülő Repó`-ban egy új, szemantikus verziót jelölő `release/*` (pl. `v1.2.0`) tag jön létre.
    2.  **Orchestráció:** A `Szülő Repó` CI pipeline-ja (az Orchestrator) elindul. Beolvassa az `ecosystem.yaml`-t, és minden `children` listában szereplő repóhoz kiküld egy eseményt, ami tartalmazza az új **release tag** nevét.
    3.  **Integráció (Renovate által):** A `Gyermek Repó`-ban a Renovate bot (vagy egy CI lépés) észleli az eseményt. A `renovate.json`-ban definiált szabályok szerint létrehoz egy `m/feature/update-parent-to-v1.2.0` nevű ágat, frissíti a függőséget a `v1.2.0`-ra, majd nyit egy Pull Request-et a `Gyermek Repó` `main` ága felé.
    4.  **Tesztelés:** A Pull Request elindítja a `Gyermek Repó` teljes CI folyamatát, ugyanúgy, mintha egy emberi fejlesztő nyitotta volna a PR-t.
    5.  **Visszacsatolás és Döntés:** A PR CI státusza (zöld vagy piros) jelzi, hogy az új release sikeresen integrálható-e. A `Gyermek Repó` tulajdonosainak (CODEOWNERS) feladata, hogy átnézzék és jóváhagyják a Pull Request-et, majd beolvasszák a `main` ágba.

*   **Eredmény:** A függőségek frissítése egy kontrollált, tesztelt, ember által jóváhagyható Pull Request formájában történik, garantálva a `main` ág stabilitását és a változások auditálhatóságát.

---

## 4. Az Eredmény: Egy Öndiagnosztizáló Irányítópult

Ez a kétsebességes modell egy olyan rendszert hoz létre, amely nem próbálja meg elrejteni a komplexitást, hanem felszínre hozza azt. A `Szülő Repó` Pull Request-jei és commit-history-ja egy valós idejű **irányítópulttá (Control Plane)** válnak, amely a teljes ökoszisztéma egészségi állapotát mutatja.

Egyetlen pillantással felmérhető, hogy egy adott változtatás mely gyermek-komponenseket "törte el", és egyértelművé válik, hogy melyik csapat felelőssége a hiba elhárítása. Ez lehetővé teszi az informált, adat-alapú döntéshozatalt ahelyett, hogy a csapatok egymásra mutogatnának egy komplex hiba esetén.
