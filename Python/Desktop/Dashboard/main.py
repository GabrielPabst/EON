# main.py
import sys
import signal
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    app.setStyle("Fusion")


    app.setQuitOnLastWindowClosed(False)

    # Ctrl+C im Terminal erlauben (bes. unter Windows braucht es einen Timer-Tick)
    signal.signal(signal.SIGINT, lambda *args: app.quit())
    app._ctrlc_tick = QTimer()
    app._ctrlc_tick.start(150)
    app._ctrlc_tick.timeout.connect(lambda: None)

    # UI starten
    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
