# app/dialogs/record_window.py
from __future__ import annotations
from typing import Optional, Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QWidget
)

from ..services.recorder_service import RecorderService
from ..widgets.record_hud import RecordHUD


class RecordWindow(QDialog):
    saved = Signal(dict)
    canceled = Signal()

    def __init__(self, recorder: RecorderService, parent=None):
        super().__init__(parent)
        self.recorder = recorder
        self._hud: Optional[RecordHUD] = None
        self._ended_unsaved = False

        self._build_ui()
        self._apply_styles()
        self._set_state(idle=True)

    def _build_ui(self):
        self.setWindowTitle("Record Macro")
        self.setMinimumWidth(640)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Create a new recording")
        title.setObjectName("title")
        root.addWidget(title)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Macro name (required)")
        root.addWidget(self._field("Name", self.name_edit))

        hint = QLabel("Mode: Full screen (fixed)")
        hint.setObjectName("hint")
        root.addWidget(hint)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Optional: describe what the macro does…")
        self.desc_wrap = self._field("Description", self.desc_edit)
        self.desc_wrap.setVisible(False)
        root.addWidget(self.desc_wrap)

        self.row_idle = self._buttons([
            ("Start recording", self._start),
            ("Close", self._close),
        ])
        self.row_after = self._buttons([
            ("Record again", self._again),
            ("Save", self._save),
            ("Close", self._close),
        ])
        root.addWidget(self.row_idle)
        root.addWidget(self.row_after)
        root.addStretch(1)

    def _field(self, label: str, w: QWidget) -> QWidget:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        l = QLabel(label)
        l.setObjectName("fieldLabel")
        v.addWidget(l)
        v.addWidget(w)
        return box

    def _buttons(self, items):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        h.addStretch(1)
        for text, fn in items:
            b = QPushButton(text)
            b.setMinimumHeight(38)
            b.clicked.connect(fn)
            h.addWidget(b)
        h.addStretch(1)
        return row

    def _apply_styles(self):
        self.setStyleSheet("""
        QDialog { background:#0a0a0a; color:#f2f2f2; }
        #title { font-size:18px; font-weight:700; margin-bottom:4px; }
        #fieldLabel { color:#9ea0a4; font-size:11px; letter-spacing:.5px; margin-left:2px; }
        #hint { color:#bbbbbb; }
        QLineEdit, QTextEdit { background:#151515; color:#fff; border:1px solid #2b2b2b; border-radius:10px; padding:8px 12px; }
        QPushButton { background:#FFB238; color:#111; border:none; border-radius:8px; padding:8px 14px; font-weight:700; }
        QPushButton:hover { background:#ffc24d; } QPushButton:pressed { background:#e5a831; }
        """)

    def _set_state(self, *, idle: bool):
        self._ended_unsaved = not idle
        self.row_idle.setVisible(idle)
        self.row_after.setVisible(not idle)
        self.desc_wrap.setVisible(not idle)

    # Actions
    def _start(self):
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        try:
            self.recorder.start_recording()
        except Exception as e:
            self._toast(f"{e}")
            return

        # HUD that also auto-closes on external stop
        self._hud = RecordHUD(
            stop_callback=self._hud_stopped,
            is_active=self.recorder.is_recording
        )
        self._hud.start()

        self.hide()
        if self.parent() and hasattr(self.parent(), "showMinimized"):
            self.parent().showMinimized()

    def _hud_stopped(self):
        try:
            self.recorder.end_recording()
        except Exception as e:
            self._toast(f"Could not stop recording: {e}")
            return
        if self._hud:
            self._hud = None
        self.showNormal(); self.raise_(); self.activateWindow()
        if self.parent() and hasattr(self.parent(), "showNormal"):
            self.parent().showNormal(); self.parent().raise_(); self.parent().activateWindow()
        self._set_state(idle=False)

    def _again(self):
        if self._hud:
            self._hud.close()
            self._hud = None
        try:
            self.recorder.discard_recording()
        except Exception:
            pass
        self._set_state(idle=True)

    def _save(self):
        name = self.name_edit.text().strip() or "New recording"
        extra: Dict = {"capture_target": "full_screen"}
        desc = (self.desc_edit.toPlainText() or "").strip()
        if desc:
            extra["description"] = desc
        try:
            meta = self.recorder.save_recording(
                name=name,
                author="",
                description=desc if desc else None,
                extra_meta=extra
            )
        except Exception as e:
            self._toast(f"Save failed: {e}")
            return
        if not meta:
            self._toast("Save failed.")
            return
        self.saved.emit(meta)
        self.accept()

    def _close(self):
        if self._hud:
            try:
                self._hud.close()
            except Exception:
                pass
            self._hud = None
        if self._ended_unsaved or self.recorder.is_recording():
            try:
                self.recorder.discard_recording()
            except Exception:
                pass
        self.canceled.emit()
        self.reject()

    def _toast(self, msg: str):
        p = self.parent()
        if p and hasattr(p, "statusBar"):
            p.statusBar().showMessage(msg, 4000)
        else:
            print(msg)
