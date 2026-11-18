import os
import sys
import pyembroidery as pe
from i18n import tr

# Formati di ricamo che pyembroidery sa leggere (le estensioni di "colori", "debug" e
# immagini, come col/edr/inf/csv/json/txt/png/svg, non sono ricami e non ci sono).
_LETTURA = ["dst", "pes", "exp", "jef", "hus", "sew", "pcs", "pec", "vp3", "xxx", "u01", "tbf",
            "dsb", "dsz", "emd", "exy", "fxy", "gt", "inb", "jpx", "ksm", "max", "mit", "new",
            "pcd", "pcm", "pcq", "phb", "phc", "shv", "spx", "stc", "stx", "tap", "zhs", "zxy",
            "100", "10o", "bro", "dat"]
# Formati in cui sappiamo SCRIVERE in modo affidabile (provati: scrittura + rilettura).
# Esclusi di proposito gcode e pmv: non producono ricami utilizzabili.
_SCRITTURA = ["pes", "dst", "exp", "jef", "pec", "vp3", "xxx", "u01", "tbf"]   # ordine del menu
# Formati che non salvano i colori dei fili (solo i cambi colore)
_SENZA_COLORI = ["dst", "exp", "u01"]


def _supportati(chiave):
    try:
        return {d["extension"] for d in pe.supported_formats() if d.get(chiave)}
    except Exception:
        return None


def _filtra(lista, chiave):
    ok = _supportati(chiave)
    return [e for e in lista if ok is None or e in ok]


ORDINE_SCRITTURA = ["." + e for e in _filtra(_SCRITTURA, "writer")]
LETTURA = {"." + e for e in _filtra(_LETTURA, "reader")}
SCRITTURA = set(ORDINE_SCRITTURA)
SENZA_COLORI = {"." + e for e in _SENZA_COLORI}


def normalizza_colori(p):
    """Alcuni formati (U01, TBF, macchine multiago) segnano il cambio colore come
    'cambio ago' invece che come 'cambio colore'. Qui li trasformo in cambi colore,
    così anteprima, conteggi e conversioni funzionano per tutti i formati."""
    if any((s[2] & pe.COMMAND_MASK) == pe.COLOR_CHANGE for s in p.stitches):
        return p
    ago = None
    ci_sono_punti = False
    for i, s in enumerate(p.stitches):
        cmd = s[2] & pe.COMMAND_MASK
        if cmd == pe.STITCH:
            ci_sono_punti = True
        elif cmd == pe.NEEDLE_SET:
            n = pe.decode_embroidery_command(s[2])[2]
            cambia = (ago is not None and n != ago) or (ago is None and ci_sono_punti)
            ago = n
            if cambia:
                p.stitches[i] = [s[0], s[1], pe.COLOR_CHANGE]
    return p


def leggi(percorso):
    """Legge un ricamo (qualunque formato supportato). None se non è leggibile."""
    p = pe.read(percorso)
    if p is None:
        return None
    return normalizza_colori(p)


def conta_punti(p):
    return sum(1 for s in p.stitches if (s[2] & pe.COMMAND_MASK) == pe.STITCH)
PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b",
           "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#000000", "#ffd700"]


def analizza(p):
    minx, miny, maxx, maxy = p.bounds()
    cambi = sum(1 for s in p.stitches
                if (s[2] & pe.COMMAND_MASK) == pe.COLOR_CHANGE)
    return (maxx - minx) / 10, (maxy - miny) / 10, cambi + 1


def percorso_libero(cartella, base, ext):
    out = os.path.join(cartella, base + ext)
    n = 1
    while os.path.exists(out):
        out = os.path.join(cartella, "%s_%d%s" % (base, n, ext))
        n += 1
    return out


def converti(src, formato, cartella_out=None):
    """Ritorna (file_creato, avvisi). Solleva eccezione se qualcosa va storto."""
    ext = "." + formato.lower().lstrip(".")
    if ext not in SCRITTURA:
        raise ValueError(tr("err_formato_uscita", ext=ext))
    p = leggi(src)
    if p is None or not p.stitches:
        raise ValueError(tr("err_non_leggibile"))

    w0, h0, blocchi0 = analizza(p)
    avvisi = []

    if ext in SENZA_COLORI:
        if p.threadlist:
            avvisi.append(tr("avv_colori_persi"))
    elif not p.threadlist:
        for i in range(blocchi0):
            h = PALETTE[i % len(PALETTE)].lstrip("#")
            n = int(h, 16)
            t = pe.EmbThread()
            t.set_color(n >> 16, (n >> 8) & 255, n & 255)
            p.add_thread(t)
        avvisi.append(tr("avv_palette"))

    if cartella_out is None:
        cartella_out = os.path.dirname(os.path.abspath(src))
    os.makedirs(cartella_out, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    out = percorso_libero(cartella_out, base, ext)

    pe.write(p, out)
    if not os.path.exists(out):
        raise ValueError(tr("err_scrittura"))

    # verifica: rileggo il file creato e confronto
    q = leggi(out)
    if q is None or not q.stitches:
        raise ValueError(tr("err_riletto"))
    w1, h1, blocchi1 = analizza(q)
    if abs(w1 - w0) > 0.5 or abs(h1 - h0) > 0.5:
        avvisi.append(tr("avv_dimensioni", w0=w0, h0=h0, w1=w1, h1=h1))
    if blocchi1 != blocchi0:
        avvisi.append(tr("avv_blocchi", a=blocchi0, b=blocchi1))
    p0, p1 = conta_punti(p), conta_punti(q)
    if abs(p0 - p1) > max(3, p0 * 0.02):      # differenze minime sono normali (punti di fermatura ecc.)
        avvisi.append(tr("avv_punti", a=p0, b=p1))
    return out, avvisi


def converti_cartella(cartella, formato, cartella_out=None):
    ext_out = "." + formato.lower().lstrip(".")
    risultati = []
    for nome in sorted(os.listdir(cartella)):
        src = os.path.join(cartella, nome)
        ext = os.path.splitext(nome)[1].lower()
        if not os.path.isfile(src) or ext not in LETTURA or ext == ext_out:
            continue
        try:
            out, avvisi = converti(src, formato, cartella_out)
            risultati.append((nome, True, avvisi))
        except Exception as e:
            risultati.append((nome, False, [str(e)]))
    return risultati


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python convert.py file_o_cartella formato [cartella_uscita]")
        sys.exit()
    bersaglio, formato = sys.argv[1], sys.argv[2]
    uscita = sys.argv[3] if len(sys.argv) > 3 else None
    if os.path.isdir(bersaglio):
        res = converti_cartella(bersaglio, formato, uscita)
        for nome, ok, avvisi in res:
            print(("OK      " if ok else "ERRORE  ") + nome)
            for a in avvisi:
                print("          - " + a)
        print("%d/%d convertiti" % (sum(1 for r in res if r[1]), len(res)))
    else:
        out, avvisi = converti(bersaglio, formato, uscita)
        print("Creato:", out)
        for a in avvisi:
            print("  - " + a)
