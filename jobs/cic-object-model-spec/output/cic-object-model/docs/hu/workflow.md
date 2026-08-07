# Fejlesztői Munkafolyamat

Ez a dokumentum a séma keretrendszerrel való interakció tipikus munkafolyamatait vázolja fel, az első beállítástól egy új kiadás létrehozásáig.

## Első Beállítás

Mielőtt elkezdenéd, győződj meg róla, hogy a következő előfeltételek telepítve vannak a gépeden:
- `docker`
- `docker-compose`
- `make`
- `git`

Kövesd ezeket a lépéseket a projekt inicializálásához a repository klónozása után:

1.  **A Vault Aláíró Ügynök Elindítása:**
    A projekthez szükség van egy futó Vault példányra a kiadási artefaktumok aláírásához. Egy segédszkript biztosított egy ideiglenes, helyi Vault szerver futtatásához fejlesztés céljából.

    ```sh
    # Ezt a projekt gyökeréből kell futtatni egy külön terminálban
    ./tools/vault-sign-agent.sh -k /eleresi/ut/a/kulcsodhoz.pem -c /eleresi/ut/a/certedhez.crt --root-ca-file /eleresi/ut/a/CICRootCA.crt
    ```
    Ez az ügynök a háttérben fog futni.

2.  **Python Függőségek Telepítése:**
    Ez a parancs lefordítja a `requirements.in` fájlt, és telepíti az összes szükséges Python csomagot egy helyi `./p_venv` könyvtárba, amelyet a Docker konténer gyorsítótárként használ.

    ```sh
    make infra.deps
    ```

3.  **Docker Image-ek Építése:**
    Építsd meg a `setup` és `builder` szolgáltatásokhoz szükséges Docker image-eket.

    ```sh
    make build
    ```

4.  **A Fejlesztői Konténer Elindítása:**
    Ez elindítja a `builder` konténert a háttérben.

    ```sh
    make up
    ```

5.  **Git Hook-ok Inicializálása:**
    Ez a szkript beállítja a `commit-msg` Git hookot, amely automatikusan aláírja a commitjaidat a futó Vault ügynök segítségével.

    ```sh
    make repo.init
    ```

A környezeted most már teljesen be van állítva és készen áll a fejlesztésre.

## Napi Fejlesztési Feladatok

Ez a tipikus ciklus, amelyet a sémák módosításakor vagy létrehozásakor követni fogsz.

1.  **Séma Módosítása:**
    Végezd el a kívánt módosításokat egy sémafájlon a `/schemas` könyvtárban.

2.  **Validálás Futtatása:**
    Mielőtt kiadást hoznál létre, elengedhetetlen a módosításaid validálása. A `validate` parancs a fordítót csak validálási módban futtatja.

    ```sh
    make validate
    ```

3.  **Tesztek Futtatása:**
    Annak érdekében, hogy maguk az eszközök is megfelelően működjenek, futtasd a `pytest` tesztcsomagot.

    ```sh
    make test
    ```

4.  **Módosítások Commit-olása:**
    Amikor készen vagy, commit-old a módosításaidat. A `commit-msg` hook automatikusan lefut, csatlakozik a helyi Vault ügynökhöz, és egy aláírási blokkot fűz a commit üzenetedhez.

    ```sh
    git add .
    git commit -m "feat: Séma frissítése új tulajdonságokkal"
    ```

## Kiadás Létrehozása

Amikor egy séma készen áll a verziózásra és terjesztésre, létrehozol egy "kiadási artefaktumot". Ez a séma egy aláírt, megváltoztathatatlan verziója.

1.  **Győződj meg róla, hogy a munkakönyvtárad tiszta:**
    A kiadási szkript leáll, ha vannak nem commit-olt módosításaid.

2.  **Futtasd a Kiadási Parancsot:**
    Használd a `make release-dependency` parancsot egy aláírt séma generálásához, amely a `/dependencies` könyvtárba kerül. A `VERSION` változónak érvényes szemantikus verziónak kell lennie (pl. `v1.2.3`).

    ```sh
    make release-dependency VERSION=v1.0.0
    ```

3.  **Tekintsd át a Folyamatot:**
    A szkript automatikusan a következő műveleteket hajtja végre:
    - Létrehoz egy új kiadási ágat (pl. `template-schema/releases/v1.0.0`).
    - Meghívja a `compiler.py` szkriptet az aláírt artefaktum generálásához.
    - Commit-olja az új artefaktumot a kiadási ágra.
    - Létrehoz egy GPG-aláírt Git taget a kiadási verzióhoz.
    - Visszavált az eredeti ágadra.

4.  **A Tag Feltöltése:**
    A kiadási folyamat egy helyi Git tag létrehozásával zárul. Ahhoz, hogy a kiadást megoszd másokkal, fel kell töltened ezt a taget a távoli repository-ba.

    ```sh
    # Példa tag névre: template-schema@v1.0.0
    git push origin <tag_neve>
    ```
