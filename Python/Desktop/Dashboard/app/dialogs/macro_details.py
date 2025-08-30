# app/dialogs/macro_details.py
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QWidget
)


class MacroDetailsDialog(QDialog):
    def __init__(self, *, name: str, description: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Macro details")
        self.setMinimumWidth(520)
        self._build_ui(name, description)
        self._apply_styles()

    def _build_ui(self, name: str, description: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel(name or "Unnamed macro")
        title.setObjectName("title")
        root.addWidget(title)

        lab = QLabel("Description")
        lab.setObjectName("fieldLabel")
        root.addWidget(lab)

        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setPlainText(description or "—")
        self.desc.setMinimumHeight(180)
        root.addWidget(self.desc, 1)

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        ok = QPushButton("Close")
        ok.clicked.connect(self.accept)
        h.addWidget(ok)
        root.addWidget(row)

    def _apply_styles(self):
        self.setStyleSheet("""
        QDialog { background:#0a0a0a; color:#f2f2f2; }
        #title { font-size:18px; font-weight:700; margin-bottom:6px; }
        #fieldLabel { color:#9ea0a4; font-size:11px; letter-spacing:.5px; margin-left:2px; }
        QTextEdit { background:#151515; color:#fff; border:1px solid #2b2b2b; border-radius:10px; padding:8px; }
        QPushButton { background:#FFB238; color:#111; border:none; border-radius:8px; padding:8px 14px; font-weight:700; }
        QPushButton:hover { background:#ffc24d; } QPushButton:pressed { background:#e5a831; }
        """)
