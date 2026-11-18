import os
import sys

NOME = "NOVAstitch"
VERSIONE = "0.1 beta"
ANNO = "2026"
AZIENDA = "Poletti Centro Cucito"
LUOGO = "Clusone (BG)"
EMAIL = "federico@poletticentrocucito.it"
SITO = ""  # facoltativo, es. "https://www.tuosito.it"


def cartella_programma():
    """Cartella del programma (dove stanno LICENZA_it.txt, LICENSE_en.txt, licenze/)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def cartelle_licenza():
    """Cartelle dove cercare LICENZA_it.txt, LICENSE_en.txt, licenze/ (Windows, Mac .app, sorgenti)."""
    c = [cartella_programma()]
    if getattr(sys, "frozen", False):
        exe = os.path.dirname(sys.executable)
        mp = getattr(sys, "_MEIPASS", None)
        if mp:
            c.append(mp)
        # dentro NOVAstitch.app: Contents/MacOS -> Contents/Resources e Contents/Frameworks
        c.append(os.path.join(exe, "..", "Resources"))
        c.append(os.path.join(exe, "..", "Frameworks"))
    return [os.path.normpath(x) for x in c]


def risorsa(nome):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "risorse", nome)
