from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QWidget, QHBoxLayout, QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal


class DropZone(QFrame):
    fileDropped = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._hover = False

        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Neues Layout-Objekt
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # Text
        self.label = QLabel("Datei hier reinziehen")
        self.label.setStyleSheet("color: #FFB238; font-size: 16px; font-weight: bold;")
        self.main_layout.addWidget(self.label)

        self.setProperty("hover", False)
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
        DropZone {
            background: transparent;
            border: 3px dashed rgba(255,178,56,0.95);
            border-radius: 14px;
        }
        DropZone[hover="true"] {
            background: rgba(255,178,56,0.07);
            border: 3px dashed #FFB238;
        }
        """)

    # Drag & drop plumbing
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._hover = True
            self.setProperty("hover", True)
            self.style().unpolish(self); self.style().polish(self)
        else:
            e.ignore()

    def dragLeaveEvent(self, _):
        self._hover = False
        self.setProperty("hover", False)
        self.style().unpolish(self); self.style().polish(self)

    def dropEvent(self, e):
        self._hover = False
        self.setProperty("hover", False)
        self.style().unpolish(self); self.style().polish(self)

        urls = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
        if urls:
            self.fileDropped.emit(urls[0])


class ImportOverlay(QDialog):
    """
    Kompakter Import-Dialog:
      - zentriert über dem Hauptfenster
      - große gestrichelte Drop-Zone (ohne Text)
      - 'Datei wählen…' Button
      - kleine Progressbar + Status
      - Esc/✕ schließt
    Ergebnis: self.file_path (oder None)
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.file_path: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # halbtransparentes Backdrop + Card
        backdrop = QWidget(self)
        backdrop.setObjectName("backdrop")
        ol = QVBoxLayout(backdrop); ol.setContentsMargins(0, 0, 0, 0)

        container = QWidget(backdrop)
        container.setObjectName("importOverlayContainer")
        container.setFixedSize(560, 360)
        ol.addWidget(container, 0, Qt.AlignCenter)
        outer.addWidget(backdrop)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        # Header
        header = QHBoxLayout(); header.setSpacing(8)
        title = QLabel("Makro importieren"); title.setObjectName("importTitle")
        btnClose = QPushButton("✕"); btnClose.setObjectName("closeBtn"); btnClose.clicked.connect(self.reject)
        header.addWidget(title); header.addStretch(1); header.addWidget(btnClose)

        # --- Drop-Zone (nur Umrandung) ---
        self.dropzone = DropZone()
        self.dropzone.fileDropped.connect(self._start_progress_and_accept)

        # Buttons
        buttons = QHBoxLayout(); buttons.setSpacing(10)
        btnFile = QPushButton("Datei wählen…"); btnFile.clicked.connect(self._browse_file)
        buttons.addStretch(1); buttons.addWidget(btnFile); buttons.addStretch(1)

        # Progress + Status
        self.progress = QProgressBar(); self.progress.setMinimum(0); self.progress.setMaximum(100)
        self.progress.setValue(0); self.progress.setTextVisible(False); self.progress.setObjectName("importProgress")
        self.status = QLabel(""); self.status.setAlignment(Qt.AlignCenter); self.status.setObjectName("statusMsg")

        lay.addLayout(header)
        # Die Zone bekommt Platz (expandiert), Button danach
        lay.addWidget(self.dropzone, 1)
        lay.addLayout(buttons)
        lay.addWidget(self.progress)
        lay.addWidget(self.status)

        self.setStyleSheet("""
        #backdrop { background: rgba(0,0,0,0.35); }
        #importOverlayContainer { background: #0f0f0f; border-radius: 14px; border:1px solid #2a2a2a; }
        #importTitle { color: white; font-size: 20px; font-weight: 800; letter-spacing:.2px; }
        #statusMsg { color:#ffb238; font-weight:700; }
        QPushButton {
            background:#FFB238; color:#111; border:none; border-radius:10px; padding:10px 16px; font-weight:800;
        }
        QPushButton:hover { background:#ffc45c; }
        #closeBtn { background: transparent; color: #ddd; padding: 4px 8px; border-radius:8px; }
        #closeBtn:hover { background: rgba(255,255,255,0.08); }
        #importProgress { background:#171717; border:1px solid #2b2b2b; border-radius:8px; height:8px; }
        QProgressBar::chunk { background:#FFB238; border-radius:8px; }
        """)

    # Zentriert über Parent anzeigen
    def showEvent(self, e):
        super().showEvent(e)
        parent = self.parentWidget()
        if parent:
            fg = self.frameGeometry()
            fg.moveCenter(parent.frameGeometry().center())
            self.move(fg.topLeft())

    # Esc schließt
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(e)

    # Dateiauswahl
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Makro-Datei wählen", "", "Log-Dateien (*.log);;Alle Dateien (*.*)"
        )
        if path:
            self._start_progress_and_accept(path)

    # Mini-Progress & Accept
    def _start_progress_and_accept(self, path: str):
        self.file_path = path
        self.status.setText("Importiere…")
        self.progress.setValue(12)

        steps = [28, 52, 78, 100]
        self._i = 0

        def tick():
            if self._i < len(steps):
                self.progress.setValue(steps[self._i])
                self._i += 1
            else:
                self.accept()
                timer.stop()

        timer = QTimer(self)
        timer.timeout.connect(tick)
        timer.start(85)
