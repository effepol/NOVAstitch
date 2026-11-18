import sys
import os
import re
import shutil
import html
from PySide6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTreeView,
                               QListView, QLabel, QLineEdit, QToolBar,
                               QComboBox, QPushButton, QMessageBox,
                               QProgressDialog, QScrollArea, QWidget, QAbstractItemView,
                               QVBoxLayout, QHBoxLayout, QFileDialog)
from PySide6.QtGui import (QPixmap, QIcon, QColor, QDesktopServices,
                           QStandardItemModel, QStandardItem, QAction,
                           QActionGroup)
try:
    from PySide6.QtWidgets import QFileSystemModel
except ImportError:
    from PySide6.QtGui import QFileSystemModel
from PySide6.QtCore import (Qt, QDir, QSize, QThreadPool, QUrl,
                            QSortFilterProxyModel, QSettings)
from convert import converti, LETTURA, ORDINE_SCRITTURA
from analisi import analizza
from render import render
from scheda_pdf import crea_pdf
from thumbs import Segnali, Lavoro, LATO, info_cache, svuota_cache
from batch import SegnaliBatch, LavoroBatch
from copia import SegnaliCopia, LavoroCopia, nome_libero
from about import FinestraInfo
from info_app import NOME, risorsa
from i18n import (tr, imposta_lingua, lingua_iniziale, salva_lingua,
                  lingue_disponibili, codice_lingua)

ESTENSIONI = LETTURA
ANTEPRIMA = 380

# ruoli dati personalizzati (256 = Qt.UserRole)
R_PATH = 256
R_NOME = 257
R_DATA = 258
R_PESO = 259
R_FORMATO = 260
R_PUNTI = 261
R_LARG = 262
R_ALT = 263
R_COLORI = 264

CRITERI = [
    ("ord_nome", R_NOME),
    ("ord_data", R_DATA),
    ("ord_peso", R_PESO),
    ("ord_formato", R_FORMATO),
    ("ord_punti", R_PUNTI),
    ("ord_larg", R_LARG),
    ("ord_alt", R_ALT),
    ("ord_colori", R_COLORI),
]
PRIMO_CRITERIO_CON_DATI = 4  # da qui in poi servono i dati delle anteprime


def chiave_nome(s):
    """Ordine naturale: nina2 prima di nina10."""
    return re.sub(r"\d+", lambda m: m.group().zfill(10), s.lower())


class Filtro(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.parole = []
        self.formato = ""
        self.setDynamicSortFilter(False)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    def imposta(self, testo, formato):
        self.parole = testo.lower().split()
        self.formato = formato
        self.invalidateFilter()

    def filterAcceptsRow(self, riga, genitore):
        idx = self.sourceModel().index(riga, 0, genitore)
        if self.formato and idx.data(R_FORMATO) != self.formato:
            return False
        nome = (idx.data() or "").lower()
        return all(p in nome for p in self.parole)


class Finestra(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(NOME)
        self.resize(1300, 750)
        self.cartella = ""
        self.generazione = 0
        self.voci = {}
        self.totale = 0
        self.fatte = 0
        self.corrente = None
        self.crescente = True
        self.msg_dettagli = ("msg_scegli_file", {})

        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(max(2, (os.cpu_count() or 4) - 1))
        self.segnali = Segnali()
        self.segnali.pronta.connect(self.miniatura_pronta)

        self.pool_batch = QThreadPool()
        self.pool_batch.setMaxThreadCount(1)
        self.segn_batch = SegnaliBatch()
        self.segn_batch.avanza.connect(self.batch_avanza)
        self.segn_batch.finito.connect(self.batch_finito)
        self.lavoro_batch = None
        self.dialogo = None

        self.pool_copia = QThreadPool()
        self.pool_copia.setMaxThreadCount(1)
        self.segn_copia = SegnaliCopia()
        self.segn_copia.avanza.connect(self.copia_avanza)
        self.segn_copia.finito.connect(self.copia_finito)
        self.lavoro_copia = None
        self.dialogo_copia = None
        self.destinazione_copia = ""

        self.segnaposto = QPixmap(LATO, LATO)
        self.segnaposto.fill(QColor("#e8e8e8"))

        # barra strumenti
        self.indirizzo = QLineEdit()
        self.indirizzo.returnPressed.connect(
            lambda: self.carica(self.indirizzo.text().strip().strip('"')))
        barra = QToolBar()
        barra.addWidget(self.indirizzo)

        self.formato = QComboBox()
        self.formato.addItems([e.lstrip(".") for e in ORDINE_SCRITTURA])
        self.b_conv_sel = QPushButton()
        self.b_conv_sel.clicked.connect(self.converti_selezionato)
        self.b_conv_cart = QPushButton()
        self.b_conv_cart.clicked.connect(self.converti_tutta_la_cartella)
        self.b_copia = QPushButton()
        self.b_copia.clicked.connect(self.copia_selezionati)
        self.b_cache = QPushButton()
        self.b_cache.clicked.connect(self.svuota_la_cache)
        barra.addWidget(self.formato)
        barra.addWidget(self.b_conv_sel)
        barra.addWidget(self.b_conv_cart)
        barra.addSeparator()
        barra.addWidget(self.b_copia)
        barra.addSeparator()
        barra.addWidget(self.b_cache)
        self.addToolBar(barra)

        # menu: Lingua, Manuale, ?
        self.menu_lingua = self.menuBar().addMenu("")
        self.gruppo_lingue = QActionGroup(self)
        self.gruppo_lingue.setExclusive(True)
        for cod, nome in lingue_disponibili():
            az = QAction(nome, self)
            az.setCheckable(True)
            az.setChecked(cod == codice_lingua())
            az.triggered.connect(lambda _=False, c=cod: self.cambia_lingua(c))
            self.gruppo_lingue.addAction(az)
            self.menu_lingua.addAction(az)

        self.az_manuale = QAction("", self)
        self.az_manuale.triggered.connect(self.apri_manuale)
        self.menu_manuale = None
        if sys.platform == "darwin":
            # su Mac le voci di primo livello senza sottomenu non compaiono
            self.menu_manuale = self.menuBar().addMenu("")
            self.menu_manuale.addAction(self.az_manuale)
        else:
            self.menuBar().addAction(self.az_manuale)

        self.menu_aiuto = self.menuBar().addMenu("?")
        self.az_info = QAction("", self)
        self.az_info.setMenuRole(QAction.AboutRole)
        self.az_info.triggered.connect(self.mostra_info)
        self.menu_aiuto.addAction(self.az_info)

        # albero cartelle
        self.modello = QFileSystemModel()
        self.modello.setRootPath("")
        self.modello.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Drives)
        self.albero = QTreeView()
        self.albero.setModel(self.modello)
        for col in (1, 2, 3):
            self.albero.hideColumn(col)
        self.albero.clicked.connect(
            lambda i: self.carica(self.modello.filePath(i)))

        # modello della lista con ordinamento e filtro
        self.modello_ric = QStandardItemModel()
        self.proxy = Filtro()
        self.proxy.setSourceModel(self.modello_ric)

        self.lista = QListView()
        self.lista.setModel(self.proxy)
        self.lista.setViewMode(QListView.IconMode)
        self.lista.setIconSize(QSize(LATO, LATO))
        self.lista.setGridSize(QSize(LATO + 24, LATO + 34))
        self.lista.setResizeMode(QListView.Adjust)
        self.lista.setMovement(QListView.Static)
        self.lista.setWordWrap(False)
        self.lista.setTextElideMode(Qt.ElideMiddle)
        self.lista.setUniformItemSizes(True)
        self.lista.setEditTriggers(QListView.NoEditTriggers)
        self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lista.selectionModel().currentChanged.connect(self.file_scelto)
        self.lista.selectionModel().selectionChanged.connect(
            lambda *_: self.aggiorna_stato())

        self.cerca = QLineEdit()
        self.cerca.setClearButtonEnabled(True)
        self.cerca.textChanged.connect(self.applica_filtro)

        self.filtro_formato = QComboBox()
        self.filtro_formato.addItem("", "")      # le voci vere si riempiono in carica()
        self.filtro_formato.currentIndexChanged.connect(self.applica_filtro)

        self.criterio = QComboBox()
        for _chiave, _ruolo in CRITERI:
            self.criterio.addItem("")
        self.criterio.currentIndexChanged.connect(self.cambia_criterio)

        self.lbl_ordina = QLabel()
        self.b_ordine = QPushButton()
        self.b_ordine.clicked.connect(self.inverti_ordine)
        self.b_tutti = QPushButton()
        self.b_tutti.clicked.connect(self.seleziona_tutti)

        centro = QWidget()
        cl = QVBoxLayout(centro)
        cl.setContentsMargins(0, 0, 0, 0)
        riga = QHBoxLayout()
        riga.addWidget(self.cerca, 1)
        riga.addWidget(self.filtro_formato)
        riga.addWidget(self.lbl_ordina)
        riga.addWidget(self.criterio)
        riga.addWidget(self.b_ordine)
        riga.addWidget(self.b_tutti)
        cl.addLayout(riga)
        cl.addWidget(self.lista, 1)

        # pannello a destra: anteprima grande + dati + pulsante PDF
        self.anteprima = QLabel()
        self.anteprima.setAlignment(Qt.AlignCenter)
        self.dettagli = QLabel()
        self.dettagli.setTextFormat(Qt.RichText)
        self.dettagli.setAlignment(Qt.AlignTop)
        self.dettagli.setWordWrap(True)
        self.dettagli.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.b_pdf = QPushButton()
        self.b_pdf.setEnabled(False)
        self.b_pdf.clicked.connect(self.crea_il_pdf)

        pannello = QWidget()
        lay = QVBoxLayout(pannello)
        lay.addWidget(self.anteprima)
        lay.addWidget(self.dettagli)
        lay.addWidget(self.b_pdf)
        lay.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(pannello)
        scroll.setMinimumWidth(420)

        split = QSplitter()
        split.addWidget(self.albero)
        split.addWidget(centro)
        split.addWidget(scroll)
        split.setSizes([240, 640, 420])
        self.setCentralWidget(split)

        self.traduci_ui()

    # ---- lingua
    def traduci_ui(self):
        """Riscrive tutti i testi fissi nella lingua corrente."""
        self.indirizzo.setPlaceholderText(tr("ui_indirizzo"))
        self.b_conv_sel.setText(tr("ui_converti_sel"))
        self.b_conv_cart.setText(tr("ui_converti_cart"))
        self.b_copia.setText(tr("ui_copia_sel"))
        self.b_tutti.setText(tr("ui_seleziona_tutti"))
        self.b_cache.setText(tr("ui_svuota_cache"))
        self.menu_lingua.setTitle(tr("menu_lingua"))
        self.az_manuale.setText(tr("menu_manuale"))
        if self.menu_manuale is not None:
            self.menu_manuale.setTitle(tr("menu_manuale"))
        self.az_info.setText(tr("menu_info", nome=NOME))
        self.cerca.setPlaceholderText(tr("ui_cerca"))
        self.filtro_formato.setItemText(0, tr("ui_tutti_formati"))
        for i, (chiave, _ruolo) in enumerate(CRITERI):
            self.criterio.setItemText(i, tr(chiave))
        self.lbl_ordina.setText(tr("ui_ordina_per"))
        self.testo_ordine()
        self.b_pdf.setText(tr("ui_crea_pdf"))
        self.ridisegna_dettagli()
        self.aggiorna_stato()

    def cambia_lingua(self, codice):
        imposta_lingua(codice)
        salva_lingua(codice)
        self.traduci_ui()

    def apri_manuale(self):
        # un solo PDF per tutte le lingue: risorse/manuale.pdf
        f = risorsa("manuale.pdf")
        if os.path.exists(f):
            QDesktopServices.openUrl(QUrl.fromLocalFile(f))
            return
        QMessageBox.information(self, NOME, tr("manuale_assente"))

    def mostra_info(self):
        FinestraInfo(self).exec()

    # ---- testi dinamici
    def imposta_msg(self, chiave, **kw):
        self.msg_dettagli = (chiave, kw)
        self.dettagli.setText(tr(chiave, **kw))

    def ridisegna_dettagli(self):
        if self.corrente is not None:
            self.dettagli.setText(self.html_dati(self.corrente[1]))
        else:
            chiave, kw = self.msg_dettagli
            self.dettagli.setText(tr(chiave, **kw))

    def aggiorna_stato(self):
        visibili = self.proxy.rowCount()
        if self.fatte < self.totale:
            testo = tr("stato_anteprime", f=self.fatte, t=self.totale)
        else:
            testo = tr("stato_pronto")
        if visibili != self.totale:
            testo += tr("stato_mostrati", v=visibili, t=self.totale)
        else:
            testo += tr("stato_file", t=self.totale)
        n_sel = len(self.lista.selectionModel().selectedIndexes())
        if n_sel > 1:
            testo += tr("stato_selezionati", n=n_sel)
        self.statusBar().showMessage(testo)

    # ---- ordinamento e filtro
    def testo_ordine(self):
        self.b_ordine.setText(tr("ord_cresc") if self.crescente
                              else tr("ord_decresc"))

    def riordina(self):
        ruolo = CRITERI[self.criterio.currentIndex()][1]
        ordine = Qt.AscendingOrder if self.crescente else Qt.DescendingOrder
        self.proxy.setSortRole(ruolo)
        self.proxy.sort(0, ordine)
        cur = self.lista.currentIndex()
        if cur.isValid():
            self.lista.scrollTo(cur)

    def cambia_criterio(self, indice):
        # nome e formato: dalla A alla Z; tutto il resto: i più grandi/recenti prima
        self.crescente = indice in (0, 3)
        self.testo_ordine()
        self.riordina()

    def inverti_ordine(self):
        self.crescente = not self.crescente
        self.testo_ordine()
        self.riordina()

    def applica_filtro(self, *_):
        self.proxy.imposta(self.cerca.text(), self.filtro_formato.currentData())
        self.aggiorna_stato()

    # ---- caricamento cartella
    def carica(self, percorso):
        self.generazione += 1
        self.pool.clear()
        self.voci = {}
        self.cartella = percorso
        self.corrente = None
        self.b_pdf.setEnabled(False)
        self.anteprima.clear()
        self.indirizzo.setText(percorso)

        modello = QStandardItemModel()
        elenco = []
        try:
            with os.scandir(percorso) as it:
                for e in it:
                    ext = os.path.splitext(e.name)[1].lower()
                    if ext in ESTENSIONI and e.is_file():
                        try:
                            st = e.stat()
                            elenco.append((e.name, st.st_mtime, st.st_size))
                        except OSError:
                            elenco.append((e.name, 0.0, 0))
        except OSError:
            self.modello_ric = modello
            self.proxy.setSourceModel(modello)
            self.aggiorna_filtro_formati([])
            self.totale = 0
            self.fatte = 0
            self.imposta_msg("msg_cartella_non_accessibile")
            self.aggiorna_stato()
            return
        elenco.sort(key=lambda v: chiave_nome(v[0]))
        self.aggiorna_filtro_formati(sorted({os.path.splitext(n)[1].lstrip(".").upper()
                                             for n, _d, _p in elenco}))

        self.totale = len(elenco)
        self.fatte = 0
        gen = self.generazione
        lavori = []
        for nome, data, peso in elenco:
            completo = os.path.join(percorso, nome)
            item = QStandardItem(QIcon(self.segnaposto), nome)
            item.setEditable(False)
            item.setToolTip(nome)
            item.setData(completo, R_PATH)
            item.setData(chiave_nome(nome), R_NOME)
            item.setData(float(data), R_DATA)
            item.setData(int(peso), R_PESO)
            item.setData(os.path.splitext(nome)[1].lstrip(".").upper(), R_FORMATO)
            item.setData(-1, R_PUNTI)
            item.setData(-1.0, R_LARG)
            item.setData(-1.0, R_ALT)
            item.setData(-1, R_COLORI)
            modello.appendRow(item)
            self.voci[completo] = item
            lavori.append(completo)

        self.modello_ric = modello
        self.proxy.setSourceModel(modello)
        self.riordina()
        for completo in lavori:
            self.pool.start(Lavoro(gen, completo, self.segnali,
                                   lambda: self.generazione))
        self.imposta_msg("msg_n_file", n=self.totale)
        self.aggiorna_stato()

    def aggiorna_filtro_formati(self, presenti):
        """Il menu dei formati mostra solo quelli che ci sono nella cartella aperta."""
        attuale = self.filtro_formato.currentData()
        self.filtro_formato.blockSignals(True)
        self.filtro_formato.clear()
        self.filtro_formato.addItem(tr("ui_tutti_formati"), "")
        for f in presenti:
            self.filtro_formato.addItem(f, f)
        i = self.filtro_formato.findData(attuale)
        self.filtro_formato.setCurrentIndex(i if i >= 0 else 0)
        self.filtro_formato.blockSignals(False)
        self.proxy.imposta(self.cerca.text(), self.filtro_formato.currentData())

    def miniatura_pronta(self, gen, percorso, img, meta):
        if gen != self.generazione:
            return
        self.fatte += 1
        item = self.voci.get(percorso)
        if item is not None:
            if img is not None:
                item.setIcon(QIcon(QPixmap.fromImage(img)))
            if meta:
                item.setData(int(meta["punti"]), R_PUNTI)
                item.setData(float(meta["larghezza"]), R_LARG)
                item.setData(float(meta["altezza"]), R_ALT)
                item.setData(int(meta["blocchi"]), R_COLORI)
        if (self.fatte >= self.totale
                and self.criterio.currentIndex() >= PRIMO_CRITERIO_CON_DATI):
            self.riordina()
        self.aggiorna_stato()

    def closeEvent(self, event):
        self.generazione += 1
        self.pool.clear()
        self.pool.waitForDone()
        if self.lavoro_batch is not None:
            self.lavoro_batch.annulla = True
            self.pool_batch.waitForDone()
        if self.lavoro_copia is not None:
            self.lavoro_copia.annulla = True
            self.pool_copia.waitForDone()
        super().closeEvent(event)

    # ---- pannello dettagli
    def html_dati(self, d):
        e = html.escape
        h = ["<b>%s</b>" % e(d["nome"]),
             "%s &middot; %.1f x %.1f mm" % (d["formato"], d["larghezza"],
                                             d["altezza"]),
             "",
             tr("det_punti", n=d["punti"]),
             tr("det_jump", n=d["jump"]),
             tr("det_rasafilo", n=d["rasafilo"]),
             tr("det_blocchi", n=d["blocchi"]),
             "",
             "<b>%s</b>" % tr("det_colori")]
        for i, (hx, desc, punti) in enumerate(d["per_blocco"]):
            h.append("<span style='color:%s'>&#9632;</span> %d. %s %s &mdash; %s"
                     % (hx, i + 1, hx, e(desc), tr("det_punti_blocco", n=punti)))
        for chiave in d["note"]:
            h.append("")
            h.append("<i>%s</i>" % e(tr(chiave)))
        return "<br>".join(h)

    def file_scelto(self, corrente, _precedente):
        if not corrente.isValid():
            return
        percorso = corrente.data(R_PATH)
        if not percorso:
            return
        self.corrente = None
        self.b_pdf.setEnabled(False)
        self.anteprima.clear()
        try:
            d, p = analizza(percorso)
        except Exception as e:
            self.imposta_msg("msg_errore", e=html.escape(str(e)))
            return
        if d is None:
            self.imposta_msg("msg_formato_non_leggibile")
            return
        self.corrente = (percorso, d, p)
        self.anteprima.setPixmap(QPixmap.fromImage(render(p, ANTEPRIMA)))
        self.ridisegna_dettagli()
        self.b_pdf.setEnabled(True)

    def crea_il_pdf(self):
        if self.corrente is None:
            QMessageBox.information(self, NOME, tr("msg_sel_file"))
            return
        percorso, d, p = self.corrente
        proposta = os.path.splitext(percorso)[0] + ".pdf"
        out, _ = QFileDialog.getSaveFileName(self, tr("pdf_salva_titolo"),
                                             proposta, tr("pdf_filtro"))
        if not out:
            return
        try:
            crea_pdf(d, p, out)
        except Exception as e:
            QMessageBox.information(self, NOME, tr("msg_errore", e=e))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(out))

    # ---- conversione
    def converti_selezionato(self):
        if self.corrente is None:
            QMessageBox.information(self, NOME, tr("msg_sel_file"))
            return
        try:
            out, avvisi = converti(self.corrente[0], self.formato.currentText())
            testo = tr("conv_creato") + "\n" + out
            if avvisi:
                testo += "\n\n" + tr("conv_attenzione") + "\n- " + "\n- ".join(avvisi)
        except Exception as e:
            testo = tr("msg_errore", e=e)
        QMessageBox.information(self, NOME, testo)
        self.carica(self.cartella)

    def converti_tutta_la_cartella(self):
        if not os.path.isdir(self.cartella):
            QMessageBox.information(self, NOME, tr("msg_apri_cartella"))
            return
        if self.lavoro_batch is not None:
            QMessageBox.information(self, NOME, tr("msg_conv_in_corso"))
            return
        self.dialogo = QProgressDialog(tr("conv_preparazione"),
                                       tr("ui_annulla"), 0, 0, self)
        self.dialogo.setWindowTitle(NOME)
        self.dialogo.setWindowModality(Qt.WindowModal)
        self.dialogo.setMinimumDuration(0)
        self.dialogo.setAutoClose(False)
        self.dialogo.setAutoReset(False)
        self.dialogo.canceled.connect(self.batch_annulla)
        self.dialogo.show()
        self.lavoro_batch = LavoroBatch(self.cartella,
                                        self.formato.currentText(),
                                        self.segn_batch)
        self.pool_batch.start(self.lavoro_batch)

    def batch_avanza(self, fatti, totale, nome):
        # setValue() su una finestra modale processa gli eventi: la finestra può
        # essere chiusa (e self.dialogo azzerato) proprio durante la chiamata,
        # quindi uso una copia locale e dopo setValue non tocco più nulla.
        dlg = self.dialogo
        if dlg is None:
            return
        dlg.setLabelText(tr("conv_label", i=fatti + 1, n=totale, nome=nome))
        dlg.setMaximum(totale)
        dlg.setValue(fatti)

    def batch_annulla(self):
        if self.lavoro_batch is not None:
            self.lavoro_batch.annulla = True
            if self.dialogo is not None:
                self.dialogo.setLabelText(tr("conv_annullamento"))

    def batch_finito(self, res, annullato, totale):
        self.lavoro_batch = None
        if self.dialogo is not None:
            self.dialogo.close()
            self.dialogo = None
        ok = sum(1 for r in res if r[1])
        if annullato:
            testo = tr("batch_annullato", ok=ok, tot=totale)
        else:
            testo = tr("batch_ok", ok=ok, n=len(res))
        problemi = ["%s: %s" % (n, "; ".join(a)) for n, r, a in res if not r or a]
        if problemi:
            testo += "\n\n" + tr("batch_controllare") + "\n" + "\n".join(problemi[:15])
            if len(problemi) > 15:
                testo += "\n" + tr("batch_altri", n=len(problemi) - 15)
        QMessageBox.information(self, NOME, testo)
        self.carica(self.cartella)

    # ---- copia dei file selezionati (per esempio su una chiavetta USB)
    def seleziona_tutti(self):
        self.lista.selectAll()
        self.lista.setFocus()

    def file_selezionati(self):
        percorsi = []
        for idx in self.lista.selectionModel().selectedIndexes():
            p = idx.data(R_PATH)
            if p and os.path.isfile(p):
                percorsi.append(p)
        percorsi.sort(key=lambda p: chiave_nome(os.path.basename(p)))
        return percorsi

    def copia_selezionati(self):
        if self.lavoro_copia is not None or self.lavoro_batch is not None:
            QMessageBox.information(self, NOME, tr("msg_copia_in_corso"))
            return
        files = self.file_selezionati()
        if not files:
            QMessageBox.information(self, NOME, tr("copia_nessuno"))
            return
        impostazioni = QSettings("NOVAstitch", "NOVAstitch")
        iniziale = str(impostazioni.value("cartella_copia", ""))
        if not os.path.isdir(iniziale):
            iniziale = os.path.expanduser("~")
        dest = QFileDialog.getExistingDirectory(self, tr("copia_scegli"), iniziale)
        if not dest:
            return
        dest = os.path.normpath(dest)
        if (os.path.normcase(os.path.abspath(dest))
                == os.path.normcase(os.path.abspath(self.cartella))):
            QMessageBox.information(self, NOME, tr("copia_stessa"))
            return
        impostazioni.setValue("cartella_copia", dest)

        # spazio libero
        serve = sum(os.path.getsize(p) for p in files)
        try:
            libero = shutil.disk_usage(dest).free
        except OSError:
            libero = None
        if libero is not None and serve > libero:
            QMessageBox.warning(self, NOME, tr("copia_spazio",
                                               serve=serve / 1048576,
                                               libero=libero / 1048576))
            return

        # file con lo stesso nome già presenti in destinazione
        nomi = [os.path.basename(p) for p in files]
        esistenti = [n for n in nomi if os.path.exists(os.path.join(dest, n))]
        sostituisci = True
        if esistenti:
            box = QMessageBox(self)
            box.setWindowTitle(NOME)
            box.setIcon(QMessageBox.Question)
            box.setText(tr("copia_esistenti", n=len(esistenti), esempio=esistenti[0]))
            b_sost = box.addButton(tr("copia_sostituisci"), QMessageBox.DestructiveRole)
            b_due = box.addButton(tr("copia_tieni_entrambi"), QMessageBox.AcceptRole)
            b_no = box.addButton(tr("ui_annulla"), QMessageBox.RejectRole)
            box.setDefaultButton(b_due)
            box.exec()
            scelto = box.clickedButton()
            if scelto is b_no or scelto is None:
                return
            sostituisci = scelto is b_sost

        coppie = []
        for p in files:
            nome = os.path.basename(p)
            if not sostituisci and os.path.exists(os.path.join(dest, nome)):
                nome = nome_libero(dest, nome)
            coppie.append((p, os.path.join(dest, nome)))
        self.destinazione_copia = dest

        self.dialogo_copia = QProgressDialog(tr("conv_preparazione"),
                                             tr("ui_annulla"), 0, 0, self)
        self.dialogo_copia.setWindowTitle(NOME)
        self.dialogo_copia.setWindowModality(Qt.WindowModal)
        self.dialogo_copia.setMinimumDuration(0)
        self.dialogo_copia.setAutoClose(False)
        self.dialogo_copia.setAutoReset(False)
        self.dialogo_copia.canceled.connect(self.copia_annulla)
        self.dialogo_copia.show()
        self.lavoro_copia = LavoroCopia(coppie, self.segn_copia)
        self.pool_copia.start(self.lavoro_copia)

    def copia_avanza(self, fatti, totale, nome):
        dlg = self.dialogo_copia      # stessa cautela di batch_avanza
        if dlg is None:
            return
        dlg.setLabelText(tr("copia_label", i=fatti + 1, n=totale, nome=nome))
        dlg.setMaximum(totale)
        dlg.setValue(fatti)

    def copia_annulla(self):
        if self.lavoro_copia is not None:
            self.lavoro_copia.annulla = True
            if self.dialogo_copia is not None:
                self.dialogo_copia.setLabelText(tr("conv_annullamento"))

    def copia_finito(self, res, annullato, totale):
        self.lavoro_copia = None
        if self.dialogo_copia is not None:
            self.dialogo_copia.close()
            self.dialogo_copia = None
        ok = sum(1 for r in res if r[1])
        if annullato:
            testo = tr("copia_annullato", ok=ok, tot=totale)
        else:
            testo = tr("copia_ok", ok=ok, dest=self.destinazione_copia)
        problemi = ["%s: %s" % (n, e) for n, r, e in res if not r]
        if problemi:
            testo += "\n\n" + tr("copia_non_copiati") + "\n" + "\n".join(problemi[:15])
            if len(problemi) > 15:
                testo += "\n" + tr("batch_altri", n=len(problemi) - 15)
        if ok:
            testo += "\n\n" + tr("copia_espelli")
        QMessageBox.information(self, NOME, testo)

    def svuota_la_cache(self):
        n, byte = info_cache()
        if n == 0:
            QMessageBox.information(self, NOME, tr("cache_vuota"))
            return
        box = QMessageBox(self)
        box.setWindowTitle(NOME)
        box.setIcon(QMessageBox.Question)
        box.setText(tr("cache_conferma", n=n, mb=byte / 1048576))
        si = box.addButton(tr("si"), QMessageBox.YesRole)
        no = box.addButton(tr("no"), QMessageBox.NoRole)
        box.setDefaultButton(no)
        box.exec()
        if box.clickedButton() is not si:
            return
        self.generazione += 1
        self.pool.clear()
        self.pool.waitForDone()
        svuota_cache()
        if self.cartella:
            self.carica(self.cartella)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(NOME)
    imposta_lingua(lingua_iniziale())
    icona = risorsa("icona.png")
    if os.path.exists(icona):
        app.setWindowIcon(QIcon(icona))
    f = Finestra()
    f.show()
    if len(sys.argv) > 1:
        f.carica(sys.argv[1])
    sys.exit(app.exec())
