import os
from PySide6.QtCore import QObject, QRunnable, Signal

PEZZO = 1024 * 1024


class SegnaliCopia(QObject):
    avanza = Signal(int, int, str)       # fatti, totale, nome del file in corso
    finito = Signal(object, bool, int)   # risultati [(nome, ok, errore)], annullato, totale


class Annullato(Exception):
    pass


def nome_libero(cartella, nome):
    """nina.dst -> nina_1.dst (o _2, _3...) se in 'cartella' esiste già."""
    base, ext = os.path.splitext(nome)
    n = 1
    while True:
        candidato = "%s_%d%s" % (base, n, ext)
        if not os.path.exists(os.path.join(cartella, candidato)):
            return candidato
        n += 1


def copia_file(src, dst, annulla=lambda: False):
    """Copia src in dst. Scrive prima in un file temporaneo (che nessuna macchina
    scambia per un ricamo), forza la scrittura sul supporto, controlla la
    dimensione e solo alla fine dà il nome definitivo. Se qualcosa va storto
    non resta nessun file a metà."""
    tmp = dst + ".nova_tmp"
    try:
        with open(src, "rb") as a, open(tmp, "wb") as b:
            while True:
                if annulla():
                    raise Annullato()
                blocco = a.read(PEZZO)
                if not blocco:
                    break
                b.write(blocco)
            b.flush()
            os.fsync(b.fileno())
        if os.path.getsize(tmp) != os.path.getsize(src):
            raise OSError("dimensione diversa dopo la copia")
        os.replace(tmp, dst)
        try:
            st = os.stat(src)
            os.utime(dst, (st.st_atime, st.st_mtime))
        except OSError:
            pass
    except BaseException:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


class LavoroCopia(QRunnable):
    def __init__(self, coppie, segnali):
        """coppie: lista di (percorso_originale, percorso_destinazione)."""
        super().__init__()
        self.setAutoDelete(False)
        self.coppie = coppie
        self.segnali = segnali
        self.annulla = False

    def run(self):
        totale = len(self.coppie)
        risultati = []
        annullato = False
        for i, (src, dst) in enumerate(self.coppie):
            if self.annulla:
                annullato = True
                break
            nome = os.path.basename(src)
            self.segnali.avanza.emit(i, totale, nome)
            try:
                copia_file(src, dst, lambda: self.annulla)
                risultati.append((nome, True, ""))
            except Annullato:
                annullato = True
                break
            except Exception as e:
                risultati.append((nome, False, str(e)))
        self.segnali.finito.emit(risultati, annullato, totale)
