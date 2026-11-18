import os
from PySide6.QtCore import QObject, QRunnable, Signal
from convert import converti, LETTURA


class SegnaliBatch(QObject):
    avanza = Signal(int, int, str)    # fatti, totale, nome del file in corso
    finito = Signal(object, bool, int)  # risultati, annullato, totale


class LavoroBatch(QRunnable):
    def __init__(self, cartella, formato, segnali):
        super().__init__()
        self.setAutoDelete(False)
        self.cartella = cartella
        self.formato = formato
        self.segnali = segnali
        self.annulla = False

    def run(self):
        ext_out = "." + self.formato.lower().lstrip(".")
        try:
            nomi = [n for n in sorted(os.listdir(self.cartella))
                    if os.path.splitext(n)[1].lower() in LETTURA
                    and os.path.splitext(n)[1].lower() != ext_out
                    and os.path.isfile(os.path.join(self.cartella, n))]
        except OSError as e:
            self.segnali.finito.emit([("(cartella)", False, [str(e)])], False, 0)
            return

        totale = len(nomi)
        risultati = []
        annullato = False
        for i, nome in enumerate(nomi):
            if self.annulla:
                annullato = True
                break
            self.segnali.avanza.emit(i, totale, nome)
            src = os.path.join(self.cartella, nome)
            try:
                out, avvisi = converti(src, self.formato)
                risultati.append((nome, True, avvisi))
            except Exception as e:
                risultati.append((nome, False, [str(e)]))
        self.segnali.finito.emit(risultati, annullato, totale)
