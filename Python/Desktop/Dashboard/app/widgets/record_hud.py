# app/widgets/record_hud.py
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication


class RecordHUD(QWidget):
    """
    Tiny always-on-top HUD showing elapsed time and a Stop button.
    Auto-closes if `is_active()` returns False (recorder ended externally) and
    will invoke `stop_callback` so the owner can transition into post-record state.
    """
    def __init__(self, stop_callback, is_active=None, parent=None):
        super().__init__(parent)
        self._stop_cb = stop_callback           # callable()
        self._is_active = is_active             # callable() -> bool, optional
        self._time = QTime(0, 0, 0)

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
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

        # 500ms: frequent enough to detect external stop quickly
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._tick)

        self.btn.clicked.connect(self._on_stop)

    def start(self):
        self._time = QTime(0, 0, 0)
        self._place_top_right()
        self.show()
        self.timer.start()

    def _tick(self):
        # External stop?
        try:
            if callable(self._is_active) and not self._is_active():
                try:
                    if callable(self._stop_cb):
                        self._stop_cb()
                finally:
                    self._shutdown()
                return
        except Exception:
            # if callback fails, keep HUD running rather than crashing
            pass

        # Update label roughly once per second
        self._time = self._time.addMSecs(self.timer.interval())
        self.lbl.setText(f"REC {self._time.toString('mm:ss')}")

    def _on_stop(self):
        try:
            if callable(self._stop_cb):
                self._stop_cb()
        finally:
            self._shutdown()

    def _shutdown(self):
        try:
            self.timer.stop()
        except Exception:
            pass
        self.close()

    def _place_top_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        margin = 12
        self.move(screen.right() - self.width() - margin, screen.top() + margin)
