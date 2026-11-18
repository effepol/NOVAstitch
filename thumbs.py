import os
import json
import hashlib
from PySide6.QtGui import QImage
from PySide6.QtCore import QObject, QRunnable, Signal
from render import render
from analisi import analizza

VERSIONE = "v1"  # se cambi il renderer, cambia questo e la cache si rigenera
LATO = 160
CARTELLA_CACHE = os.path.join(os.path.expanduser("~"), ".novastitch", "cache")


def chiave(percorso):
    st = os.stat(percorso)
    s = "%s|%s|%s|%s|%s" % (VERSIONE, LATO, os.path.abspath(percorso),
                            st.st_mtime_ns, st.st_size)
    return hashlib.sha1(s.encode("utf-8", "replace")).hexdigest()


def miniatura(percorso):
    """Ritorna (QImage o None, dati o None), dalla cache o appena calcolati."""
    os.makedirs(CARTELLA_CACHE, exist_ok=True)
    base = os.path.join(CARTELLA_CACHE, chiave(percorso))
    f_png = base + ".png"
    f_json = base + ".json"
    if os.path.exists(f_png) and os.path.exists(f_json):
        img = QImage(f_png)
        try:
            with open(f_json, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            meta = None
        if not img.isNull() and meta is not None:
            return img, meta
    d, p = analizza(percorso)
    if d is None:
        return None, None
    img = render(p, LATO)
    meta = {k: d[k] for k in ("punti", "rasafilo", "blocchi",
                              "larghezza", "altezza")}
    img.save(f_png, "PNG")
    with open(f_json, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    return img, meta


class Segnali(QObject):
    pronta = Signal(int, str, object, object)


class Lavoro(QRunnable):
    def __init__(self, gen, percorso, segnali, gen_attuale):
        super().__init__()
        self.gen = gen
        self.percorso = percorso
        self.segnali = segnali
        self.gen_attuale = gen_attuale

    def run(self):
        if self.gen_attuale() != self.gen:
            return
        try:
            img, meta = miniatura(self.percorso)
        except Exception:
            img, meta = None, None
        self.segnali.pronta.emit(self.gen, self.percorso, img, meta)


def info_cache():
    n = 0
    byte = 0
    if os.path.isdir(CARTELLA_CACHE):
        for nome in os.listdir(CARTELLA_CACHE):
            low = nome.lower()
            if low.endswith((".png", ".json")):
                try:
                    byte += os.path.getsize(os.path.join(CARTELLA_CACHE, nome))
                    if low.endswith(".png"):
                        n += 1
                except OSError:
                    pass
    return n, byte


def svuota_cache():
    n = 0
    if os.path.isdir(CARTELLA_CACHE):
        for nome in os.listdir(CARTELLA_CACHE):
            low = nome.lower()
            if low.endswith((".png", ".json")):
                try:
                    os.remove(os.path.join(CARTELLA_CACHE, nome))
                    if low.endswith(".png"):
                        n += 1
                except OSError:
                    pass
    return n
