from PySide6.QtCore import QObject, Signal
import time

class Worker(QObject):
    progressed = Signal(int)
    finished = Signal()
    canceled = Signal()

    def __init__(self):
        super().__init__()
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        for i in range(101):
            if self._cancel:
                self.canceled.emit()
                return
            self.progressed.emit(i)
            time.sleep(0.03)
        self.finished.emit()
