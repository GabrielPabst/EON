from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt


class SideNav(QWidget):
    requestImport = Signal()
    requestSettings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideNav")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        title = QLabel("Navigation")
        title.setObjectName("sideNavTitle")

        btnImport = QPushButton("Importieren")
        btnSettings = QPushButton("Einstellungen")

        for b in (btnImport, btnSettings):
            b.setCursor(Qt.PointingHandCursor)

        btnImport.clicked.connect(self.requestImport.emit)
        btnSettings.clicked.connect(self.requestSettings.emit)

        lay.addWidget(title)
        lay.addWidget(btnImport)
        lay.addWidget(btnSettings)
        lay.addStretch(1)

        self.setStyleSheet("""
        #sideNav { background:#0b0b0b; border-left:1px solid #2a2a2a; }
        #sideNavTitle { color:#cfcfcf; font-weight:700; margin:6px 0 8px 4px; }
        QPushButton { background:#171717; color:#eee; border:1px solid #2a2a2a; border-radius:12px; padding:10px 12px; }
        QPushButton:hover { border-color:#3a3a3a; background:#1e1e1e; }
        """)
