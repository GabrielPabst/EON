# app/widgets/record_hud.py
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication

class RecordHUD(QWidget):
    """
    Small floating HUD (always-on-top) that shows elapsed time and a Stop button.
    Emits no signals; caller passes a stop_callback to be invoked when Stop is clicked.
    """
    def __init__(self, stop_callback, parent=None):
        super().__init__(parent)
        self._stop_cb = stop_callback
        self._time = QTime(0, 0, 0)

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            QWidget { background: rgba(20,20,20, 220); border-radius: 12px; }
            QLabel { color: #fff; font-weight: 700; }
            QPushButton { background:#FF4D4D; color:#111; border:none; border-radius:8px; padding:6px 10px; font-weight:700; }
            QPushButton:hover { background:#ff6b6b; }
            QPushButton:pressed { background:#e24a4a; }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(12)

        self.dot = QLabel("●")
        self.dot.setStyleSheet("color:#ff4d4d; font-size:18px;")
        self.lbl = QLabel("REC 00:00")
        self.btn = QPushButton("Stop")

        lay.addWidget(self.dot)
        lay.addWidget(self.lbl)
        lay.addStretch(1)
        lay.addWidget(self.btn)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

        self.btn.clicked.connect(self._on_stop)

    def start(self):
        self._time = QTime(0, 0, 0)
        self.timer.start()
        self._place_top_right()
        self.show()

    def _tick(self):
        self._time = self._time.addSecs(1)
        self.lbl.setText(f"REC {self._time.toString('mm:ss')}")

    def _on_stop(self):
        try:
            if callable(self._stop_cb):
                self._stop_cb()
        finally:
            self.timer.stop()
            self.close()

    def _place_top_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        margin = 12
        self.move(screen.right() - self.width() - margin, screen.top() + margin)
