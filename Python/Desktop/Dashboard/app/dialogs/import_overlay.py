from __future__ import annotations

import os
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QWidget, QHBoxLayout, QProgressBar, QFrame, QSizePolicy
)


class DropZone(QFrame):
    pathDropped = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._hover = False

        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel("Drop ZIP or folder here")
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

    # Drag & drop
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
        if not urls:
            return
        p = urls[0]
        # Only accept ZIP files or directories
        if os.path.isdir(p) or p.lower().endswith(".zip"):
            self.pathDropped.emit(p)
        else:
            # could show a gentle hint via parent dialog label if desired
            pass


class ImportOverlay(QDialog):
    """
    Compact import dialog:
      - Accepts ZIP or folder (macro package)
    Result:
      self.selected_path: str | None
      self.selected_kind: str in {"zip","folder"} | None
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.selected_path: str | None = None
        self.selected_kind: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Backdrop + card
        backdrop = QWidget(self)
        backdrop.setObjectName("backdrop")
        ol = QVBoxLayout(backdrop); ol.setContentsMargins(0, 0, 0, 0)

        container = QWidget(backdrop)
        container.setObjectName("importOverlayContainer")
        container.setFixedSize(560, 380)
        ol.addWidget(container, 0, Qt.AlignCenter)
        outer.addWidget(backdrop)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        # Header
        header = QHBoxLayout(); header.setSpacing(8)
        title = QLabel("Import macro (ZIP/Folder)")
        title.setObjectName("importTitle")
        btnClose = QPushButton("✕"); btnClose.setObjectName("closeBtn"); btnClose.clicked.connect(self.reject)
        header.addWidget(title); header.addStretch(1); header.addWidget(btnClose)

        # Drop-zone
        self.dropzone = DropZone()
        self.dropzone.pathDropped.connect(self._start_progress_and_accept)

        # Buttons (ZIP / Folder only)
        buttons = QHBoxLayout(); buttons.setSpacing(10)
        btnZip = QPushButton("Choose ZIP…"); btnZip.clicked.connect(self._browse_zip)
        btnDir = QPushButton("Choose folder…"); btnDir.clicked.connect(self._browse_folder)
        buttons.addStretch(1); buttons.addWidget(btnZip); buttons.addWidget(btnDir); buttons.addStretch(1)

        # Progress + status
        self.progress = QProgressBar(); self.progress.setMinimum(0); self.progress.setMaximum(100)
        self.progress.setValue(0); self.progress.setTextVisible(False); self.progress.setObjectName("importProgress")
        self.status = QLabel(""); self.status.setAlignment(Qt.AlignCenter); self.status.setObjectName("statusMsg")

        lay.addLayout(header)
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

    # Center over parent
    def showEvent(self, e):
        super().showEvent(e)
        parent = self.parentWidget()
        if parent:
            fg = self.frameGeometry()
            fg.moveCenter(parent.frameGeometry().center())
            self.move(fg.topLeft())

    # ESC closes
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(e)

    # Browsers
    def _browse_zip(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose macro ZIP", "", "ZIP files (*.zip)")
        if path:
            self._start_progress_and_accept(path)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose macro folder", "")
        if path:
            self._start_progress_and_accept(path)

    # Progress & accept
    def _start_progress_and_accept(self, path: str):
        # only accept ZIP or folder
        if os.path.isdir(path):
            kind = "folder"
        elif path.lower().endswith(".zip"):
            kind = "zip"
        else:
            self.status.setText("Only ZIP or folder is supported.")
            return

        self.selected_path = path
        self.selected_kind = kind

        self.status.setText("Importing…")
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
