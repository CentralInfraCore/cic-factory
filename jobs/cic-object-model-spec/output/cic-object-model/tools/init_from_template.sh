#!/bin/bash

# Szigorú mód: a szkript kilép, ha egy parancs hibával tér vissza.
set -e

# --- Változók és paraméterek ---
SOURCE_REPO_URL=$1
SOURCE_BRANCH=$2
DEST_REPO_URL=$3

# --- Bemeneti paraméterek ellenőrzése ---
if [ -z "$SOURCE_REPO_URL" ] || [ -z "$SOURCE_BRANCH" ] || [ -z "$DEST_REPO_URL" ]; then
  echo "Hiba: Hiányzó paraméterek!"
  echo "Használat: $0 <forrás_repo_url> <forrás_ág> <cél_repo_url>"
  echo "Példa: $0 https://github.com/felhasznalo/repo.git feature-A https://github.com/XXX/YYY.git"
  exit 1
fi

# --- Biztonsági ellenőrzés: Ne fusson a forrás repóban! ---
# Ellenőrizzük, hogy egyáltalán egy git repóban vagyunk-e.
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  # Ha igen, lekérjük az 'origin' remote URL-jét.
  CURRENT_ORIGIN_URL=$(git remote get-url origin)

  # Összehasonlítjuk a jelenlegi origin-t a szkriptnek megadott forrás URL-lel.
  if [ "$CURRENT_ORIGIN_URL" == "$SOURCE_REPO_URL" ]; then
    echo "------------------------------------------------------------------"
    echo "!!! BIZTONSÁGI HIBA !!!"
    echo "A szkriptet egy olyan repositoryban próbálod futtatni,"
    echo "amelynek 'origin'-je megegyezik a megadott forrás repositoryval."
    echo "Ez a szkript csak új repositoryk inicializálására szolgál."
    echo "Kilépés a véletlen károkozás elkerülése érdekében."
    echo "------------------------------------------------------------------"
    exit 1
  fi
fi

# A cél könyvtár nevének kinyerése a cél URL-ből (pl. YYY.git -> YYY)
LOCAL_DIR_NAME=$(basename "$DEST_REPO_URL" .git)

echo ">>> 1. Forrás repository klónozása a(z) '$SOURCE_BRANCH' ágról..."
git clone -b "$SOURCE_BRANCH" --single-branch "$SOURCE_REPO_URL" "$LOCAL_DIR_NAME"

# Belépés az új könyvtárba
cd "$LOCAL_DIR_NAME"
echo "Belépés a(z) '$LOCAL_DIR_NAME' könyvtárba."

echo ">>> 2. 'main' ág létrehozása és beállítása fő ágnak..."
git checkout -b main

echo ">>> 3. Eredeti 'origin' remote átnevezése 'base'-re..."
git remote rename origin base

echo ">>> 4. Új 'origin' remote hozzáadása a cél repositoryhoz..."
git remote add origin "$DEST_REPO_URL"

echo ">>> 5. 'main' ág feltöltése az új 'origin' repositoryba..."
# A -u kapcsoló beállítja a "tracking"-et a jövőbeli push/pull parancsokhoz
git push -u origin main

echo ">>> 6. Felesleges lokális '$SOURCE_BRANCH' ág törlése..."
git branch -d "$SOURCE_BRANCH"

echo "------------------------------------------------------------------"
echo "KÉSZ! Az új repository sikeresen inicializálva a(z) '$LOCAL_DIR_NAME' könyvtárban."
echo "A 'main' ág feltöltve ide: $DEST_REPO_URL"
echo "Az eredeti forrás repository 'base' néven érhető el."
echo "------------------------------------------------------------------"
