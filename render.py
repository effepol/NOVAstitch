import sys
import pyembroidery as pe
from PySide6.QtGui import QImage, QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPointF
from convert import PALETTE


def colori(p):
    if p.threadlist:
        return [QColor(t.hex_color()) for t in p.threadlist]
    return [QColor(c) for c in PALETTE]


def disegna(qp, p, scala, ox, oy, cols, spessore):
    """scala = pixel per unità (1/10 mm); (ox, oy) = dove cade l'angolo in alto a sinistra."""
    minx, miny, maxx, maxy = p.bounds()
    idx = 0
    pen = QPen(cols[0])
    pen.setWidthF(spessore)
    pen.setCapStyle(Qt.RoundCap)
    qp.setPen(pen)
    pos = None
    for x, y, c in p.stitches:
        cmd = c & pe.COMMAND_MASK
        pt = QPointF((x - minx) * scala + ox, (y - miny) * scala + oy)
        if cmd == pe.STITCH:
            if pos is not None:
                qp.drawLine(pos, pt)
        elif cmd == pe.COLOR_CHANGE:
            idx += 1
            pen.setColor(cols[idx % len(cols)])
            qp.setPen(pen)
            continue
        if cmd in (pe.STITCH, pe.JUMP, pe.TRIM):
            pos = pt


def render(p, lato=800, sfondo="#ffffff"):
    minx, miny, maxx, maxy = p.bounds()
    w = max(maxx - minx, 1)
    h = max(maxy - miny, 1)
    margine = 20
    scala = (lato - 2 * margine) / max(w, h)
    img = QImage(int(w * scala) + 2 * margine, int(h * scala) + 2 * margine,
                 QImage.Format_ARGB32)
    img.fill(QColor(sfondo))
    qp = QPainter(img)
    qp.setRenderHint(QPainter.Antialiasing)
    disegna(qp, p, scala, margine, margine, colori(p), max(1.0, 4 * scala))
    qp.end()
    return img


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python render.py file.dst uscita.png [sfondo]")
        sys.exit()
    p = pe.read(sys.argv[1])
    if p is None:
        print("Formato non leggibile")
        sys.exit()
    sfondo = sys.argv[3] if len(sys.argv) > 3 else "#ffffff"
    render(p, 800, sfondo).save(sys.argv[2])
    print("Salvato:", sys.argv[2])
