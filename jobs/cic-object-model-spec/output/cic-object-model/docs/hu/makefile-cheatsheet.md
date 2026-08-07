# Makefile Súgó

Ez a fájl tartalmazza az összes elérhető `make` parancs és azok funkcióinak teljes listáját.

## Konténer Életciklus

- `make up`: Elindítja a `builder` fejlesztői konténert a háttérben. A konténer futva marad, amíg explicit módon le nem állítják.
- `make down`: Leállít és eltávolít minden, a projekthez tartozó konténert, hálózatot és kötetet.
- `make shell`: Interaktív `bash` shellt nyit a futó `builder` konténeren belül. Ez az elsődleges módja a fejlesztői környezettel való interakciónak.
- `make build`: Megépíti vagy újraépíti a `setup` és `builder` szolgáltatásokhoz tartozó Docker image-eket.

## Fő Fejlesztési Feladatok

- `make validate`: A sémafordítót csak validálási módban futtatja. Ellenőrzi a `/schemas` könyvtárban lévő forrás sémákat a meta-sémában definiált szabályok alapján.
- `make test`: Végrehajtja a Python alapú eszközök `pytest` tesztcsomagját. Ez magában foglalja a fordító unit tesztjeit is.
- `make fmt`: Automatikusan formázza az összes Python kódot a `black` és `isort` eszközökkel a konzisztens kódstílus biztosítása érdekében.
- `make lint`: Ellenőrzi a Python kódot a `ruff` és az összes YAML fájlt a `yamllint` eszközzel a lehetséges hibák és stílusproblémák kiszűrésére.
- `make typecheck`: Statikus típusanalízist futtat a Python kódbázison a `mypy` segítségével.
- `make check`: Egy kényelmi parancs, amely sorban futtatja a `fmt`, `lint` és `typecheck` parancsokat.

## Kiadáskezelés

- `make release-dependency VERSION=<verzió>`: Ez az elsődleges parancs egy aláírt, verziózott artefaktum létrehozásához. Egy `VERSION` argumentumot vár (pl. `v1.2.3`), és egy aláírt sémafájlt generál a `/dependencies` könyvtárba. A folyamat magában foglalja a validálást, ellenőrzőösszeg-számítást, Vaulton keresztüli aláírást, valamint egy új Git ág és tag létrehozását a kiadáshoz.
- `make release-schema VERSION=<verzió>`: Hasonló a `release-dependency`-hez, de végleges, alkalmazás-specifikus sémák létrehozására szolgál. Az aláírt artefaktumot a `/release` könyvtárba helyezi.

## Repository Beállítása

- `make repo.init`: Beállítja a Git hook-okat ehhez a repository-hoz. Jelenleg a `commit-msg` hookot telepíti, amely automatikusan aláírja a commitokat egy helyi Vault ügynök segítségével. Ezt a parancsot a repository klónozása után egyszer kell futtatni.

## Infrastruktúra és Karbantartás

- `make infra.deps`: (Újra)generálja a `requirements.txt` fájlt a `requirements.in` alapján, és telepíti az összes Python függőséget a helyi `./p_venv` gyorsítótárba. Futtasd ezt a parancsot, miután hozzáadtál vagy eltávolítottál egy függőséget a `requirements.in` fájlban.
- `make infra.coverage`: HTML tesztlefedettségi jelentést generál a `./htmlcov` könyvtárba. Ez részletes képet ad arról, hogy a kód mely részeit fedik le a tesztek.
- `make infra.clean`: Egy takarító parancs, amely leállít minden konténert, eltávolít minden generált fájlt (mint a `./p_venv`, `requirements.txt`), és töröl minden gyorsítótárat és Docker kötetet. Ez hasznos, ha teljesen tiszta állapotból szeretnél indulni.
