import os
import pyembroidery as pe
from convert import PALETTE, leggi


def analizza(percorso):
    """Ritorna (dati, pattern). Se il file non è leggibile: (None, None).

    d["note"] contiene chiavi di traduzione, non testi: si traducono al momento
    di mostrarle (così il cambio lingua si applica anche ai dati già letti).
    """
    p = leggi(percorso)
    if p is None or not p.stitches:
        return None, None
    minx, miny, maxx, maxy = p.bounds()
    conta = {}
    per_blocco = [0]
    for x, y, c in p.stitches:
        n = c & pe.COMMAND_MASK
        conta[n] = conta.get(n, 0) + 1
        if n == pe.STITCH:
            per_blocco[-1] += 1
        elif n == pe.COLOR_CHANGE:
            per_blocco.append(0)

    ext = os.path.splitext(percorso)[1].lower()
    blocchi = []
    for i, punti in enumerate(per_blocco):
        if p.threadlist:
            t = p.threadlist[i % len(p.threadlist)]
            blocchi.append((t.hex_color(), getattr(t, "description", "") or "", punti))
        else:
            blocchi.append((PALETTE[i % len(PALETTE)], "", punti))

    note = []
    if not p.threadlist:
        note.append("nota_no_colori")
    if ext in (".dst", ".exp"):
        note.append("nota_trim")

    d = {
        "nome": os.path.basename(percorso),
        "cartella": os.path.dirname(os.path.abspath(percorso)),
        "formato": ext.lstrip(".").upper(),
        "byte": os.path.getsize(percorso),
        "larghezza": (maxx - minx) / 10,
        "altezza": (maxy - miny) / 10,
        "punti": conta.get(pe.STITCH, 0),
        "jump": conta.get(pe.JUMP, 0),
        "rasafilo": conta.get(pe.TRIM, 0),
        "cambi": conta.get(pe.COLOR_CHANGE, 0),
        "blocchi": conta.get(pe.COLOR_CHANGE, 0) + 1,
        "per_blocco": blocchi,
        "note": note,
    }
    return d, p
