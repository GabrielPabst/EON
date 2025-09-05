from __future__ import annotations
import os
import ast
import re
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QDialogButtonBox, QLabel, QMessageBox, QSlider, QWidget, QHBoxLayout, QPushButton
)

_ASSIGN_RE = re.compile(r"^\s*(?P<key>\w+)\s*=\s*(?P<val>.+?)\s*(#.*)?$")

def _find_python_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name.lower() == "python":
            return parent
    return here.parents[3]

def _locate_config(env_var: str, folder_name: str) -> Optional[Path]:
    p = os.environ.get(env_var)
    if p:
        cfg = Path(p) / "config.py"
        if cfg.exists():
            return cfg
    pr = _find_python_root()
    cand = pr / folder_name / "config.py"
    if cand.exists():
        return cand
    return None

def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""

def _parse_assigns(text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for line in text.splitlines():
        m = _ASSIGN_RE.match(line)
        if not m:
            continue
        k = m.group("key")
        raw = m.group("val").strip()
        try:
            out[k] = ast.literal_eval(raw)
        except Exception:
            out[k] = raw.strip("'\"")
    return out

def _format_py(v: Any) -> str:
    return repr(v)

def _rewrite_config(original: str, updates: Dict[str, Any]) -> str:
    lines = original.splitlines()
    written = set()
    for i, line in enumerate(lines):
        m = _ASSIGN_RE.match(line)
        if not m:
            continue
        k = m.group("key")
        if k in updates:
            lines[i] = f"{k} = {_format_py(updates[k])}"
            written.add(k)
    for k, v in updates.items():
        if k not in written:
            lines.append(f"{k} = {_format_py(v)}")
    out = "\n".join(lines)
    if not out.endswith("\n"):
        out += "\n"
    return out

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.mc_cfg = _locate_config("EON_MACRO_CLIENT", "Makro-Client")
        self.rc_cfg = _locate_config("EON_RECORDER_CLIENT", "Recorder-Client")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        if not self.mc_cfg or not self.rc_cfg:
            warn = QLabel()
            warn.setWordWrap(True)
            warn.setStyleSheet("color:#ffcf73;")
            msgs = []
            if not self.mc_cfg:
                msgs.append("Macro Client config not found. Set EON_MACRO_CLIENT or place the folder next to “Python”.")
            if not self.rc_cfg:
                msgs.append("Recorder Client config not found. Set EON_RECORDER_CLIENT or place the folder next to “Python”.")
            warn.setText("\n".join(msgs))
            root.addWidget(warn)

        self._factory_mc: Dict[str, Any] = {
            "DEFAULT_THRESHOLD": 0.6,
            "CONFIDENCE_THRESHOLD": 0.8,
            "MAX_ATTEMPTS": 3,
            "RETRY_DELAY": 2.0,
            "SEARCH_REGION_SIZE": 100,
        }
        self._factory_rc: Dict[str, Any] = {
            "STOP_KEY": "q",
        }

        self._initial_mc: Dict[str, Any] = {}
        self._initial_rc: Dict[str, Any] = {}

        self.mc_fields: Dict[str, object] = {}
        if self.mc_cfg:
            mc_vals = _parse_assigns(_read_text(self.mc_cfg))
            self._initial_mc = {
                "DEFAULT_THRESHOLD": float(mc_vals.get("DEFAULT_THRESHOLD", self._factory_mc["DEFAULT_THRESHOLD"])),
                "CONFIDENCE_THRESHOLD": float(mc_vals.get("CONFIDENCE_THRESHOLD", self._factory_mc["CONFIDENCE_THRESHOLD"])),
                "MAX_ATTEMPTS": int(mc_vals.get("MAX_ATTEMPTS", self._factory_mc["MAX_ATTEMPTS"])),
                "RETRY_DELAY": float(mc_vals.get("RETRY_DELAY", self._factory_mc["RETRY_DELAY"])),
                "SEARCH_REGION_SIZE": int(mc_vals.get("SEARCH_REGION_SIZE", self._factory_mc["SEARCH_REGION_SIZE"])),
            }

            mc_group = QGroupBox("Macro Client")
            mc_form = QFormLayout(mc_group)

            self._add_double_slider(mc_form, "Template match threshold:", "DEFAULT_THRESHOLD",
                                    self._initial_mc["DEFAULT_THRESHOLD"], 0.0, 1.0, 0.01)
            self._add_double_slider(mc_form, "Click-screenshot confidence:", "CONFIDENCE_THRESHOLD",
                                    self._initial_mc["CONFIDENCE_THRESHOLD"], 0.0, 1.0, 0.01)
            self._add_spin(mc_form, "Max retries:", "MAX_ATTEMPTS",
                           self._initial_mc["MAX_ATTEMPTS"], 1, 50)
            self._add_double_spin(mc_form, "Retry delay (s):", "RETRY_DELAY",
                                  self._initial_mc["RETRY_DELAY"], 0.0, 30.0, 0.1, 2)
            self._add_spin(mc_form, "Search region size (px):", "SEARCH_REGION_SIZE",
                           self._initial_mc["SEARCH_REGION_SIZE"], 10, 2000)

            root.addWidget(mc_group)

        self.rc_fields: Dict[str, object] = {}
        if self.rc_cfg:
            rc_vals = _parse_assigns(_read_text(self.rc_cfg))
            self._initial_rc = {"STOP_KEY": str(rc_vals.get("STOP_KEY", self._factory_rc["STOP_KEY"]))}

            rc_group = QGroupBox("Recorder Client")
            rc_form = QFormLayout(rc_group)
            stop = self._initial_rc["STOP_KEY"]
            w_stop = QLineEdit(stop); w_stop.setMaxLength(1)
            rc_form.addRow("Recorder stop key:", w_stop)
            self.rc_fields["STOP_KEY"] = w_stop
            root.addWidget(rc_group)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self._btn_revert = QPushButton("Revert")
        self._btn_defaults = QPushButton("Restore defaults")
        btns.addButton(self._btn_revert, QDialogButtonBox.ResetRole)
        btns.addButton(self._btn_defaults, QDialogButtonBox.ResetRole)
        self._btn_revert.clicked.connect(self._reset_to_initial)
        self._btn_defaults.clicked.connect(self._apply_factory_defaults)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self.setStyleSheet("""
        QDialog { background:#0a0a0a; color:#f2f2f2; }
        QGroupBox { border:1px solid #2b2b2b; border-radius:10px; margin-top:10px; padding:12px;}
        QGroupBox::title { subcontrol-origin: margin; left:10px; padding:0 4px; color:#cfcfcf; }
        QLabel { color:#cfcfcf; }
        QLineEdit, QDoubleSpinBox, QSpinBox {
            background:#151515; color:#fff; border:1px solid #2b2b2b; border-radius:8px; padding:6px 8px;
        }
        QDialogButtonBox QPushButton { background:#FFB238; color:#111; border:none; border-radius:8px; padding:8px 14px; font-weight:700; }
        QDialogButtonBox QPushButton:hover { background:#ffc24d; } QDialogButtonBox QPushButton:pressed { background:#e5a831; }
        """)

    def _add_double_slider(self, form: QFormLayout, label: str, key: str,
                           value: float, lo: float, hi: float, step: float):
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(int(round((hi - lo) / step)))
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setSingleStep(step)
        spin.setDecimals(3)
        def _set_from_val(v: float):
            spin.setValue(v)
            slider.setValue(int(round((v - lo) / step)))
        def _on_slider(v: int):
            spin.setValue(lo + v * step)
        def _on_spin(v: float):
            slider.setValue(int(round((v - lo) / step)))
        slider.valueChanged.connect(_on_slider)
        spin.valueChanged.connect(_on_spin)
        _set_from_val(float(value))
        row = QWidget()
        h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(10)
        h.addWidget(slider, 1); h.addWidget(spin, 0)
        form.addRow(label, row)
        self.mc_fields[key] = {"spin": spin, "slider": slider, "lo": lo, "hi": hi, "step": step}

    def _add_double_spin(self, form: QFormLayout, label: str, key: str,
                         value: float, lo: float, hi: float, step: float, decimals: int = 2):
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setSingleStep(step)
        w.setDecimals(decimals)
        w.setValue(float(value))
        form.addRow(label, w)
        self.mc_fields[key] = w

    def _add_spin(self, form: QFormLayout, label: str, key: str,
                  value: int, lo: int, hi: int):
        w = QSpinBox()
        w.setRange(lo, hi)
        w.setValue(int(value))
        form.addRow(label, w)
        self.mc_fields[key] = w

    def _reset_to_initial(self):
        if self.mc_fields:
            dt = self.mc_fields.get("DEFAULT_THRESHOLD")
            if isinstance(dt, dict):
                dt["spin"].setValue(float(self._initial_mc["DEFAULT_THRESHOLD"]))  # type: ignore[index]
            ct = self.mc_fields.get("CONFIDENCE_THRESHOLD")
            if isinstance(ct, dict):
                ct["spin"].setValue(float(self._initial_mc["CONFIDENCE_THRESHOLD"]))  # type: ignore[index]
            ma = self.mc_fields.get("MAX_ATTEMPTS")
            if hasattr(ma, "setValue"):
                ma.setValue(int(self._initial_mc["MAX_ATTEMPTS"]))  # type: ignore[attr-defined]
            rd = self.mc_fields.get("RETRY_DELAY")
            if hasattr(rd, "setValue"):
                rd.setValue(float(self._initial_mc["RETRY_DELAY"]))  # type: ignore[attr-defined]
            sr = self.mc_fields.get("SEARCH_REGION_SIZE")
            if hasattr(sr, "setValue"):
                sr.setValue(int(self._initial_mc["SEARCH_REGION_SIZE"]))  # type: ignore[attr-defined]
        if self.rc_fields:
            stop = self.rc_fields.get("STOP_KEY")
            if hasattr(stop, "setText"):
                stop.setText(str(self._initial_rc.get("STOP_KEY", self._factory_rc["STOP_KEY"])))  # type: ignore[attr-defined]

    def _apply_factory_defaults(self):
        if self.mc_fields:
            dt = self.mc_fields.get("DEFAULT_THRESHOLD")
            if isinstance(dt, dict):
                dt["spin"].setValue(float(self._factory_mc["DEFAULT_THRESHOLD"]))  # type: ignore[index]
            ct = self.mc_fields.get("CONFIDENCE_THRESHOLD")
            if isinstance(ct, dict):
                ct["spin"].setValue(float(self._factory_mc["CONFIDENCE_THRESHOLD"]))  # type: ignore[index]
            ma = self.mc_fields.get("MAX_ATTEMPTS")
            if hasattr(ma, "setValue"):
                ma.setValue(int(self._factory_mc["MAX_ATTEMPTS"]))  # type: ignore[attr-defined]
            rd = self.mc_fields.get("RETRY_DELAY")
            if hasattr(rd, "setValue"):
                rd.setValue(float(self._factory_mc["RETRY_DELAY"]))  # type: ignore[attr-defined]
            sr = self.mc_fields.get("SEARCH_REGION_SIZE")
            if hasattr(sr, "setValue"):
                sr.setValue(int(self._factory_mc["SEARCH_REGION_SIZE"]))  # type: ignore[attr-defined]
        if self.rc_fields:
            stop = self.rc_fields.get("STOP_KEY")
            if hasattr(stop, "setText"):
                stop.setText(str(self._factory_rc["STOP_KEY"]))  # type: ignore[attr-defined]

    def _save(self):
        if self.mc_cfg:
            orig = _read_text(self.mc_cfg)
            if not orig:
                QMessageBox.critical(self, "Error", f"Cannot read file:\n{self.mc_cfg}")
                return
            def _val_of(key: str) -> float:
                obj = self.mc_fields[key]
                if isinstance(obj, dict):
                    return float(obj["spin"].value())  # type: ignore[index]
                return float(obj.value())  # type: ignore[attr-defined]
            updates_mc = {
                "DEFAULT_THRESHOLD": _val_of("DEFAULT_THRESHOLD"),
                "CONFIDENCE_THRESHOLD": _val_of("CONFIDENCE_THRESHOLD"),
                "MAX_ATTEMPTS": int(self.mc_fields["MAX_ATTEMPTS"].value()),  # type: ignore[attr-defined]
                "RETRY_DELAY": float(self.mc_fields["RETRY_DELAY"].value()),  # type: ignore[attr-defined]
                "SEARCH_REGION_SIZE": int(self.mc_fields["SEARCH_REGION_SIZE"].value()),  # type: ignore[attr-defined]
            }
            new_mc = _rewrite_config(orig, updates_mc)
            try:
                self.mc_cfg.write_text(new_mc, encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed:\n{self.mc_cfg}\n{e}")
                return

        if self.rc_cfg:
            orig = _read_text(self.rc_cfg)
            if not orig:
                QMessageBox.critical(self, "Error", f"Cannot read file:\n{self.rc_cfg}")
                return
            stop = self.rc_fields["STOP_KEY"].text().strip()  # type: ignore[attr-defined]
            if len(stop) != 1:
                QMessageBox.warning(self, "Invalid", "Recorder stop key must be exactly one character.")
                return
            updates_rc = {"STOP_KEY": stop}
            new_rc = _rewrite_config(orig, updates_rc)
            try:
                self.rc_cfg.write_text(new_rc, encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed:\n{self.rc_cfg}\n{e}")
                return

        QMessageBox.information(self, "Saved", "Settings saved.")
        self.accept()
