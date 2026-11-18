from PySide6.QtGui import QPdfWriter, QPageSize, QPainter, QPen, QColor, QFont
from PySide6.QtCore import QPointF, QRectF, QMarginsF, Qt
from render import colori, disegna
from info_app import NOME, AZIENDA, EMAIL
from i18n import tr

DPI = 300
M = 15          # margine in mm
LARG = 180      # larghezza utile in mm (A4 = 210)
ALT_PAG = 297
MAX_BLOCCHI = 40


def crea_pdf(d, p, out):
    def m(v):
        return v * DPI / 25.4

    w = QPdfWriter(out)
    w.setResolution(DPI)
    w.setPageSize(QPageSize(QPageSize.A4))
    w.setPageMargins(QMarginsF(0, 0, 0, 0))
    w.setTitle(d["nome"])
    qp = QPainter(w)
    if not qp.isActive():
        raise OSError(tr("pdf_errore_scrittura"))
    qp.setRenderHint(QPainter.Antialiasing)

    def penna(colore, spessore_mm):
        pen = QPen(QColor(colore))
        pen.setWidthF(m(spessore_mm))
        return pen

    def scrivi(x, y, s, pt=10, bold=False, colore="#000000", largh=None):
        f = QFont()
        f.setPointSizeF(pt)
        f.setBold(bold)
        qp.setFont(f)
        qp.setPen(QColor(colore))
        if largh is not None:
            s = qp.fontMetrics().elidedText(s, Qt.ElideMiddle, int(m(largh)))
        qp.drawText(QPointF(m(x), m(y)), s)

    def piede():
        scrivi(M, ALT_PAG - 8, "%s - %s - %s" % (NOME, AZIENDA, EMAIL),
               7, False, "#999999")

    # --- intestazione
    y = M + 6
    scrivi(M, y, d["nome"], 16, True, largh=LARG)
    y += 6
    scrivi(M, y, d["cartella"], 8, False, "#666666", LARG)
    y += 4
    qp.setPen(penna("#999999", 0.3))
    qp.drawLine(QPointF(m(M), m(y)), QPointF(m(M + LARG), m(y)))
    y += 7

    # --- dati
    righe = [
        (tr("pdf_formato"), d["formato"]),
        (tr("pdf_dimensioni"), "%.1f x %.1f mm" % (d["larghezza"], d["altezza"])),
        (tr("pdf_punti"), str(d["punti"])),
        (tr("pdf_jump"), str(d["jump"])),
        (tr("pdf_rasafilo"), str(d["rasafilo"])),
        (tr("pdf_cambi"), str(d["cambi"])),
        (tr("pdf_blocchi"), str(d["blocchi"])),
        (tr("pdf_peso"), "%.1f KB" % (d["byte"] / 1024)),
    ]
    for etichetta, valore in righe:
        scrivi(M, y, etichetta, 10, False, "#666666")
        scrivi(M + 45, y, valore, 10, True)
        y += 5.5

    # --- colori (due colonne)
    y += 3
    scrivi(M, y, tr("pdf_colori"), 11, True)
    y += 6
    blocchi = d["per_blocco"]
    mostra = [b for i, b in enumerate(blocchi) if i < MAX_BLOCCHI]
    righe_n = (len(mostra) + 1) // 2
    for i, (hx, desc, punti) in enumerate(mostra):
        col = 0 if i < righe_n else 1
        r = i if col == 0 else i - righe_n
        x = M + col * 92
        yy = y + r * 5
        qp.fillRect(QRectF(m(x), m(yy - 3.2), m(3.5), m(3.5)), QColor(hx))
        qp.setPen(penna("#888888", 0.15))
        qp.setBrush(Qt.NoBrush)
        qp.drawRect(QRectF(m(x), m(yy - 3.2), m(3.5), m(3.5)))
        testo = tr("pdf_colore_riga", i=i + 1, hx=hx, desc=desc, n=punti)
        scrivi(x + 6, yy, testo, 8, False, "#000000", 84)
    y += righe_n * 5 + 2
    if len(blocchi) > MAX_BLOCCHI:
        scrivi(M, y, tr("pdf_altri", n=len(blocchi) - MAX_BLOCCHI),
               8, False, "#666666")
        y += 5
    for chiave in d["note"]:
        scrivi(M, y, tr(chiave), 8, False, "#666666", LARG)
        y += 4

    # --- disegno: 1:1 se ci sta nella pagina, altrimenti pagina nuova
    w_mm = max(d["larghezza"], 0.1)
    h_mm = max(d["altezza"], 0.1)
    # Se il disegno ha la stessa scala in prima pagina e in una pagina intera
    # (tipico dei ricami larghi e bassi), resta in prima pagina; la seconda
    # pagina serve solo quando lì verrebbe più grande.
    libero = ALT_PAG - M - y - 12
    area_h = ALT_PAG - 2 * M - 14
    f1 = max(0.0, min(1.0, LARG / w_mm, libero / h_mm))
    f2 = min(1.0, LARG / w_mm, area_h / h_mm)
    if f1 >= f2 - 1e-9:
        fattore = f1
        top = y + 4
    else:
        piede()
        w.newPage()
        top = M + 2
        fattore = f2

    larg_d = w_mm * fattore
    alt_d = h_mm * fattore
    left = M + (LARG - larg_d) / 2

    qp.setPen(penna("#bbbbbb", 0.2))
    qp.setBrush(Qt.NoBrush)
    qp.drawRect(QRectF(m(left - 2), m(top - 2), m(larg_d + 4), m(alt_d + 4)))

    scala = m(0.1 * fattore)
    spessore = max(m(0.4 * fattore), m(0.15))
    disegna(qp, p, scala, m(left), m(top), colori(p), spessore)

    if fattore == 1.0:
        didascalia = tr("pdf_didascalia_reale", w=d["larghezza"], h=d["altezza"])
    else:
        didascalia = tr("pdf_didascalia_scala", pct=round(fattore * 100),
                        w=d["larghezza"], h=d["altezza"])
    scrivi(M, top + alt_d + 7, didascalia, 8, False, "#444444", LARG)

    piede()
    qp.end()
