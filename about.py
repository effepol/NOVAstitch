import os
import html
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QTextBrowser, QPushButton)
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtCore import Qt, QUrl
from info_app import (NOME, VERSIONE, ANNO, AZIENDA, LUOGO, EMAIL, SITO, risorsa,
                      cartelle_licenza)
from i18n import tr, codice_lingua


def file_licenza():
    """Licenza nella lingua corrente (se manca, nell'altra). None se non c'è."""
    ordine = ["LICENZA_it.txt", "LICENSE_en.txt"]
    if codice_lingua() != "it":
        ordine.reverse()
    for nome in ordine:
        for base in cartelle_licenza():
            f = os.path.join(base, nome)
            if os.path.exists(f):
                return f
    return None


def testo_html():
    e = html.escape
    kw = dict(nome=e(NOME), azienda=e(AZIENDA), luogo=e(LUOGO))
    contatti = "%s &mdash; %s<br>%s: <a href='mailto:%s'>%s</a>" % (
        kw["azienda"], kw["luogo"], tr("about_email"), e(EMAIL), e(EMAIL))
    if SITO:
        contatti += "<br>%s: <a href='%s'>%s</a>" % (tr("about_web"), e(SITO), e(SITO))
    parti = [
        "<p>%s</p>" % tr("about_intro", **kw),
        "<h3>%s</h3>" % tr("about_h_chi"),
        "<p>%s</p>" % tr("about_chi", **kw),
        "<h3>%s</h3>" % tr("about_h_termini"),
        "<p>%s</p>" % tr("about_termini_intro", **kw),
        "<ul><li>%s</li><li>%s</li><li>%s</li></ul>" % (
            tr("about_t1", **kw), tr("about_t2", **kw), tr("about_t3", **kw)),
        "<p>%s</p>" % tr("about_diritti", **kw),
        "<p>%s</p>" % tr("about_garanzia", **kw),
        "<h3>%s</h3>" % tr("about_h_terzi"),
        "<p>%s</p>" % tr("about_terzi", **kw),
        "<h3>%s</h3>" % tr("about_h_contatti"),
        "<p>%s</p>" % contatti,
        "<p><small>&copy; %s %s</small></p>" % (e(ANNO), kw["azienda"]),
    ]
    return "\n".join(parti)


class FinestraInfo(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("about_titolo", nome=NOME))
        self.resize(560, 660)
        lay = QVBoxLayout(self)

        testa = QHBoxLayout()
        logo = QLabel()
        png = risorsa("icona.png")
        if os.path.exists(png):
            logo.setPixmap(QPixmap(png).scaled(
                96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        titolo = QLabel("<span style='font-size:24pt'><b>%s</b></span><br>%s" % (
            html.escape(NOME), html.escape(tr("about_versione", v=VERSIONE))))
        testa.addWidget(logo)
        testa.addWidget(titolo, 1)
        lay.addLayout(testa)

        testo = QTextBrowser()
        testo.setOpenExternalLinks(True)
        testo.setHtml(testo_html())
        lay.addWidget(testo, 1)

        riga = QHBoxLayout()
        riga.addStretch(1)
        self.licenza = file_licenza()
        if self.licenza:
            b_lic = QPushButton(tr("about_licenza"))
            b_lic.clicked.connect(self.apri_licenza)
            riga.addWidget(b_lic)
        chiudi = QPushButton(tr("about_chiudi"))
        chiudi.clicked.connect(self.accept)
        riga.addWidget(chiudi)
        lay.addLayout(riga)

    def apri_licenza(self):
        if self.licenza:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.licenza))
