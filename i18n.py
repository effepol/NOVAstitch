import os
import json
from PySide6.QtCore import QSettings, QLocale
from info_app import risorsa

_testi = {}
_base = {}
_codice = "it"
_pronto = False


def cartella_lingue():
    return risorsa("lingue")


def _leggi(codice):
    try:
        percorso = os.path.join(cartella_lingue(), codice + ".json")
        with open(percorso, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def lingue_disponibili():
    """Lista di (codice, nome) ordinata per nome, letta dai file in risorse/lingue."""
    out = []
    try:
        nomi = sorted(os.listdir(cartella_lingue()))
    except OSError:
        return out
    for n in nomi:
        if n.lower().endswith(".json"):
            cod = n[:-5]
            d = _leggi(cod)
            if d:
                out.append((cod, str(d.get("_nome", cod))))
    out.sort(key=lambda v: v[1].lower())
    return out


def imposta_lingua(codice):
    """Carica la lingua scelta. Le chiavi mancanti ripiegano su inglese, poi italiano."""
    global _testi, _base, _codice, _pronto
    base = {}
    base.update(_leggi("it"))
    base.update(_leggi("en"))
    _base = base
    _testi = _leggi(codice)
    _codice = codice
    _pronto = True


def codice_lingua():
    return _codice


def lingua_iniziale():
    """Lingua salvata, altrimenti quella del sistema, altrimenti inglese."""
    disponibili = [c for c, _n in lingue_disponibili()]
    salvata = str(QSettings("NOVAstitch", "NOVAstitch").value("lingua", ""))
    if salvata in disponibili:
        return salvata
    sistema = QLocale.system().name().split("_")[0].lower()
    if sistema in disponibili:
        return sistema
    if "en" in disponibili:
        return "en"
    return disponibili[0] if disponibili else "en"


def salva_lingua(codice):
    QSettings("NOVAstitch", "NOVAstitch").setValue("lingua", codice)


def tr(chiave, **kw):
    if not _pronto:
        imposta_lingua("it")
    s = _testi.get(chiave)
    if s is None:
        s = _base.get(chiave)
    if s is None:
        s = chiave
    if kw:
        try:
            return s.format(**kw)
        except (KeyError, IndexError, ValueError):
            return s
    return s
