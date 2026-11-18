#!/bin/bash
# NOVAstitch - costruzione per Mac: crea NOVAstitch.app e il file NOVAstitch-0.1.dmg
# Uso (nel Terminale, dentro questa cartella):   bash costruisci_mac.command
cd "$(dirname "$0")" || exit 1
VERSIONE="0.1"

fine() { echo; echo "$1"; echo; read -r -p "Premi Invio per chiudere..." _; exit "${2:-1}"; }

[ "$(uname)" = "Darwin" ] || fine "Questo script serve solo su Mac." 1

# --- 1. trova un Python adatto (3.10 o piu' recente, meglio quello di python.org)
PY=""
for c in python3.13 python3.14 python3.12 python3.11 python3.10 \
         /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 python3; do
  p="$(command -v "$c" 2>/dev/null)" || continue
  if "$p" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] < (3,16) else 1)' 2>/dev/null; then PY="$p"; break; fi
done
[ -n "$PY" ] || fine "Non trovo Python 3.10 o piu' recente. Installa Python 3.13 da https://www.python.org/downloads/macos/ e rilancia."
echo "Python usato: $PY ($("$PY" --version))"

# --- 2. ambiente virtuale
if [ ! -x venv/bin/python ]; then
  echo; echo "[1/5] Creo l'ambiente virtuale..."
  "$PY" -m venv venv || fine "Impossibile creare l'ambiente virtuale."
fi
VP="venv/bin/python"
echo; echo "[2/5] Installo i componenti (serve internet)..."
"$VP" -m pip install --upgrade pip >/dev/null 2>&1
"$VP" -m pip install -r requirements-build.txt || fine "Installazione dei componenti fallita. Leggi i messaggi sopra."

# --- 3. architettura: universal2 (Apple Silicon + Intel) se Python lo permette, altrimenti quella di questo Mac
ARCHI="$(lipo -archs "$("$VP" -c 'import sys; print(sys.executable)')" 2>/dev/null)"
unset NOVA_ARCH
case "$ARCHI" in *arm64*x86_64*|*x86_64*arm64*) export NOVA_ARCH=universal2 ;; esac
[ -n "$FORZA_ARCH" ] && export NOVA_ARCH="$FORZA_ARCH"
echo; echo "[3/5] Costruisco NOVAstitch.app (architettura: ${NOVA_ARCH:-questo Mac})..."
rm -rf build dist
if ! "$VP" -m PyInstaller --noconfirm --clean NOVAstitch_mac.spec; then
  if [ "$NOVA_ARCH" = "universal2" ]; then
    echo; echo "Versione universal2 non riuscita: riprovo solo per questo Mac."
    unset NOVA_ARCH; rm -rf build dist
    "$VP" -m PyInstaller --noconfirm --clean NOVAstitch_mac.spec || fine "ERRORE nella costruzione. Leggi i messaggi sopra."
  else
    fine "ERRORE nella costruzione. Leggi i messaggi sopra."
  fi
fi
APP="dist/NOVAstitch.app"
[ -d "$APP" ] || fine "NOVAstitch.app non e' stata creata."

# --- 4. firma "ad hoc" (gratuita, obbligatoria sui Mac Apple Silicon) e controllo
echo; echo "[4/5] Firma ad hoc e controlli..."
xattr -cr "$APP"
codesign --force --deep --sign - "$APP" || fine "codesign fallito."
codesign --verify --deep --strict "$APP" && echo "Firma ad hoc: OK"
lipo -archs "$APP/Contents/MacOS/NOVAstitch" 2>/dev/null | sed 's/^/Architetture: /'

# prova di avvio senza finestra: il programma deve restare vivo qualche secondo
QT_QPA_PLATFORM=offscreen "$APP/Contents/MacOS/NOVAstitch" >/tmp/novastitch_prova.log 2>&1 &
PID=$!
sleep 6
if kill -0 "$PID" 2>/dev/null; then echo "Prova di avvio: OK"; kill "$PID" 2>/dev/null
else echo "ATTENZIONE: il programma si e' chiuso subito. Vedi /tmp/novastitch_prova.log"; cat /tmp/novastitch_prova.log; fine "Prova di avvio fallita."; fi

# --- 5. immagine disco (.dmg)
echo; echo "[5/5] Creo il file .dmg..."
rm -rf dmg_staging; mkdir dmg_staging
cp -R "$APP" dmg_staging/
ln -s /Applications dmg_staging/Applications
cp LICENZA_it.txt LICENSE_en.txt dmg_staging/
cp -R licenze dmg_staging/licenze
cp LEGGIMI_MAC.txt dmg_staging/
mkdir -p installer_output
DMG="installer_output/NOVAstitch-$VERSIONE.dmg"
rm -f "$DMG"
hdiutil create -volname "NOVAstitch" -srcfolder dmg_staging -ov -format UDZO "$DMG" || fine "hdiutil fallito."
rm -rf dmg_staging
echo; echo "FATTO. Il file da distribuire e': $DMG"
open installer_output
read -r -p "Premi Invio per chiudere..." _
