import os
import sys
from typing import Optional, List

from PySide6 import QtCore, QtGui, QtWidgets

import zipfile
import tempfile

# Ensure we can import user's backend module when running next to this file
# If action_log_manager.py is in the same folder, this works. Otherwise, adjust sys.path as needed.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from action_log_manager import (
    ActionsLogManager,
    ActionEvent,
    EventType,
    KeyType,
    ValidationError,
)


# -----------------------------
# Utilities
# -----------------------------

def human_time(t: float) -> str:
    try:
        return f"{t:.3f}"
    except Exception:
        return str(t)


def resolve_screenshot_path(log_path: Optional[str], screenshot_value: Optional[str]) -> Optional[str]:
    if not screenshot_value:
        return None
    if os.path.isabs(screenshot_value):
        return screenshot_value if os.path.exists(screenshot_value) else None
    # resolve relative to the log file directory if known
    base_dir = os.path.dirname(log_path) if log_path else os.getcwd()
    full = os.path.normpath(os.path.join(base_dir, screenshot_value))
    return full if os.path.exists(full) else None


# -----------------------------
# Qt Model for the table
# -----------------------------
class EventTableModel(QtCore.QAbstractTableModel):
    HEADERS = ["#", "Type", "Key", "Time", "X", "Y", "Screenshot"]

    def __init__(self, manager: ActionsLogManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.filtered_indices: List[int] = list(range(len(self.manager.events)))
        self.filter_text = ""

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.filtered_indices)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.filtered_indices[index.row()]
        event = self.manager.events[row]

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            start_time = self.manager.events[0].time if self.manager.events else None
            col = index.column()
            if col == 0:
                return row
            elif col == 1:
                return event.type
            elif col == 2:
                return event.key
            elif col == 3:
                return human_time(event.time-start_time) + "s"
            elif col == 4:
                return "" if event.x is None else str(event.x)
            elif col == 5:
                return "" if event.y is None else str(event.y)
            elif col == 6:
                return event.screenshot or ""

        if role == QtCore.Qt.TextAlignmentRole:
            if index.column() in (0, 3, 4, 5):
                return QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        if role == QtCore.Qt.ForegroundRole and index.column() == 1:
            # color press/release for quick scanning
            if event.type == EventType.PRESS.value:
                return QtGui.QBrush(QtGui.QColor(34, 139, 34))  # green-ish
            elif event.type == EventType.RELEASE.value:
                return QtGui.QBrush(QtGui.QColor(178, 34, 34))  # red-ish

        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return self.HEADERS[section]
        return int(section)

    def refresh(self):
        self.apply_filter(self.filter_text)

    def apply_filter(self, text: str):
        self.beginResetModel()
        self.filter_text = text.strip().lower()
        if not self.filter_text:
            self.filtered_indices = list(range(len(self.manager.events)))
        else:
            filt = self.filter_text
            self.filtered_indices = []
            for i, e in enumerate(self.manager.events):
                blob = f"{e.type} {e.key} {e.time} {e.x} {e.y} {e.screenshot}".lower()
                if filt in blob:
                    self.filtered_indices.append(i)
        self.endResetModel()

    def map_to_real_index(self, proxy_row: int) -> int:
        return self.filtered_indices[proxy_row]

    def map_from_real_index(self, real_row: int) -> Optional[int]:
        try:
            return self.filtered_indices.index(real_row)
        except ValueError:
            return None


# -----------------------------
# Event Editor Dialog
# -----------------------------
# Modified EventEditorDialog class with automatic coordinate field handling

class EventEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, *, manager: ActionsLogManager, event: Optional[ActionEvent] = None):
        super().__init__(parent)
        self.setWindowTitle("Event Editor")
        self.manager = manager
        self._build_ui()
        self._populate_keys()
        if event:
            self._load_event(event)
        # Set initial state based on current type
        self._on_type_changed()

    def _build_ui(self):
        layout = QtWidgets.QFormLayout(self)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems([EventType.PRESS.value, EventType.RELEASE.value])
        # Connect the type combo to handle coordinate field state
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        self.key_combo = QtWidgets.QComboBox()
        self.key_combo.setEditable(True)
        self.key_combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.key_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

        self.time_spin = QtWidgets.QDoubleSpinBox()
        self.time_spin.setDecimals(6)
        self.time_spin.setRange(0.0, 1e15)
        self.time_spin.setSingleStep(0.001)

        self.x_spin = QtWidgets.QSpinBox()
        self.x_spin.setRange(-99999, 99999)
        self.x_null = QtWidgets.QCheckBox("None")
        self.x_null.setChecked(False)

        self.y_spin = QtWidgets.QSpinBox()
        self.y_spin.setRange(-99999, 99999)
        self.y_null = QtWidgets.QCheckBox("None")
        self.y_null.setChecked(False)

        self.ss_edit = QtWidgets.QLineEdit()
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        ss_layout = QtWidgets.QHBoxLayout()
        ss_layout.addWidget(self.ss_edit)
        ss_layout.addWidget(browse_btn)

        layout.addRow("Type", self.type_combo)
        layout.addRow("Key", self.key_combo)
        layout.addRow("Time", self.time_spin)

        x_layout = QtWidgets.QHBoxLayout()
        x_layout.addWidget(self.x_spin)
        x_layout.addWidget(self.x_null)
        layout.addRow("X", x_layout)

        y_layout = QtWidgets.QHBoxLayout()
        y_layout.addWidget(self.y_spin)
        y_layout.addWidget(self.y_null)
        layout.addRow("Y", y_layout)

        layout.addRow("Screenshot", ss_layout)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

        self.setLayout(layout)
        self.setMinimumWidth(420)

    def _on_type_changed(self):
        """Handle coordinate fields based on event type"""
        current_type = self.type_combo.currentText().lower()
        is_mouse_event = "mouse" in current_type
        
        # Enable/disable coordinate fields
        self.x_spin.setEnabled(is_mouse_event)
        self.x_null.setEnabled(is_mouse_event)
        self.y_spin.setEnabled(is_mouse_event)
        self.y_null.setEnabled(is_mouse_event)
        
        # Apply visual styling for disabled state
        if not is_mouse_event:
            # Set coordinates to None and check the None checkboxes
            self.x_null.setChecked(True)
            self.y_null.setChecked(True)
            # Apply grayed out style
            self.x_spin.setStyleSheet("QSpinBox { color: #666; background: #1a1a1a; }")
            self.y_spin.setStyleSheet("QSpinBox { color: #666; background: #1a1a1a; }")
            self.x_null.setStyleSheet("QCheckBox { color: #666; }")
            self.y_null.setStyleSheet("QCheckBox { color: #666; }")
        else:
            # Restore normal styling
            self.x_spin.setStyleSheet("")
            self.y_spin.setStyleSheet("")
            self.x_null.setStyleSheet("")
            self.y_null.setStyleSheet("")

    def _populate_keys(self):
        keys = self.manager.get_valid_keys()
        self.key_combo.addItems(keys)

    def _load_event(self, e: ActionEvent):
        self.type_combo.setCurrentText(e.type)
        # ensure existing key is present even if not in enum
        if self.key_combo.findText(e.key) < 0:
            self.key_combo.addItem(e.key)
        self.key_combo.setCurrentText(e.key)
        start_time = self.manager.events[0].time if self.manager.events else None
        self.time_spin.setValue(float(e.time)-start_time if e.time is not None else 0.0)
        
        if e.x is None:
            self.x_null.setChecked(True)
        else:
            self.x_null.setChecked(False)
            self.x_spin.setValue(e.x)
            
        if e.y is None:
            self.y_null.setChecked(True)
        else:
            self.y_null.setChecked(False)
            self.y_spin.setValue(e.y)
            
        self.ss_edit.setText(e.screenshot or "")

    def values(self):
        current_type = self.type_combo.currentText().lower()
        is_mouse_event = "mouse" in current_type
        
        # For non-mouse events, always return None for coordinates
        if not is_mouse_event:
            x_val = None
            y_val = None
        else:
            x_val = None if self.x_null.isChecked() else int(self.x_spin.value())
            y_val = None if self.y_null.isChecked() else int(self.y_spin.value())
            
        start_time = self.manager.events[0].time if self.manager.events else None

        return {
            "type": self.type_combo.currentText(),
            "key": self.key_combo.currentText().strip(),
            "time": float(self.time_spin.value()+start_time),
            "x": x_val,
            "y": y_val,
            "screenshot": self.ss_edit.text().strip() or None,
        }

    def _browse(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Screenshot")
        if fn:
            self.ss_edit.setText(fn)

# -----------------------------
# Frontend
# -----------------------------
class ActionLogFrontend(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Actions Log Viewer ✨")
        self.resize(1200, 720)

        self.manager = ActionsLogManager()
        self._build_ui()
        self._apply_style()

    # UI Assembly
    def _build_ui(self):
        # Hide the menubar
        self.menuBar().hide()
        
        # Central splitter
        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Horizontal)
        self.setCentralWidget(splitter)

        # Left side: table + toolbar + filter
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_toolbar = self._build_toolbar()
        left_layout.addWidget(left_toolbar)

        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Filter events (type, key, time, x/y, screenshot)…")
        self.filter_edit.textChanged.connect(self._on_filter)
        left_layout.addWidget(self.filter_edit)

        self.table_model = EventTableModel(self.manager)
        self.table = QtWidgets.QTableView()
        self.table.setModel(self.table_model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.selectionModel().selectionChanged.connect(self._sync_selection_from_table)
        self.table.doubleClicked.connect(lambda _: self.edit_event())
        left_layout.addWidget(self.table, 1)

        # Right side: vertical splitter with timeline and screenshot preview
        right = QtWidgets.QSplitter()
        right.setOrientation(QtCore.Qt.Vertical)

        # Timeline - Initialize with empty data first
        from zoomable_timeline import ZoomableTimeline
        self.timeline = ZoomableTimeline(event_data=[], mouse_moves_log_path="")
        right.addWidget(self._wrap_in_group("zoomable timeline", self.timeline))

        # Screenshot preview
        self.preview_label = QtWidgets.QLabel("No screenshot")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setFrameShape(QtWidgets.QFrame.StyledPanel)
        right.addWidget(self._wrap_in_group("Screenshot Preview", self.preview_label))

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([650, 550])

        # Menus
        self._build_menus()

        # Status bar
        self.status = self.statusBar()
        self.status.showMessage("Ready")

    def _wrap_in_group(self, title: str, w: QtWidgets.QWidget) -> QtWidgets.QWidget:
        gb = QtWidgets.QGroupBox(title)
        lay = QtWidgets.QVBoxLayout(gb)
        lay.addWidget(w)
        return gb

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QToolBar()
        bar.setIconSize(QtCore.QSize(20, 20))

        open_act = QtGui.QAction("Open", self)
        open_act.triggered.connect(self.open_file)
        save_act = QtGui.QAction("Save", self)
        save_act.triggered.connect(self.save_file)
        validate_act = QtGui.QAction("Validate", self)
        validate_act.triggered.connect(self.validate_events)
        add_act = QtGui.QAction("Add", self)
        add_act.triggered.connect(self.add_event)
        edit_act = QtGui.QAction("Edit", self)
        edit_act.triggered.connect(self.edit_event)
        del_act = QtGui.QAction("Delete", self)
        del_act.triggered.connect(self.delete_event)

        for a in (open_act, save_act, validate_act, add_act, edit_act, del_act):
            bar.addAction(a)
        return bar

    def _build_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        open_act = QtGui.QAction("Open…", self)
        open_act.triggered.connect(self.open_file)
        save_act = QtGui.QAction("Save", self)
        save_act.triggered.connect(self.save_file)
        exit_act = QtGui.QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addActions([open_act, save_act])
        file_menu.addSeparator()
        file_menu.addAction(exit_act)

        edit_menu = menubar.addMenu("&Edit")
        add_act = QtGui.QAction("Add Event…", self)
        add_act.triggered.connect(self.add_event)
        edit_act = QtGui.QAction("Edit Selected…", self)
        edit_act.triggered.connect(self.edit_event)
        del_act = QtGui.QAction("Delete Selected", self)
        del_act.triggered.connect(self.delete_event)
        edit_menu.addActions([add_act, edit_act, del_act])

        tools_menu = menubar.addMenu("&Tools")
        validate_act = QtGui.QAction("Validate Events", self)
        validate_act.triggered.connect(self.validate_events)
        tools_menu.addAction(validate_act)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QMainWindow { background: #0f1115; }
            QWidget { color: #E6E6E6; font-size: 13px; }
            QTableView { background: #151823; gridline-color: #2a2f3a; }
            QHeaderView::section { background: #1d2130; padding: 6px; border: none; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #1a1e2b; border: 1px solid #2a2f3a; padding: 4px 6px; border-radius: 6px; }
            QGroupBox { border: 1px solid #2a2f3a; border-radius: 10px; margin-top: 10px; padding: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QListView { background: #151823; }
            QToolBar { background: #141827; border: none; }
            QPushButton { background: #2a2f3a; border: none; padding: 6px 10px; border-radius: 8px; }
            QPushButton:hover { background: #334; }
            QStatusBar { background: #141827; }
            """
        )

    def _refresh_timeline(self):
        """Convert manager events to timeline format and refresh"""
        if hasattr(self, 'timeline'):
            # Convert your ActionEvent objects to the format expected by timeline
            timeline_events = []
            for i, event in enumerate(self.manager.events):
                # Ensure time is a float, not a string or other type
                event_time = float(event.time) if event.time is not None else 0.0
                
                timeline_events.append({
                    'index': i,
                    'type': event.type,
                    'key': event.key,
                    'time': event_time,
                    'x': event.x if event.x is not None else 0,
                    'y': event.y if event.y is not None else 0,
                    'screenshot': event.screenshot
                })
            
            # Update timeline with new data using load_data method
            self.timeline.load_data(None, timeline_events, self.manager.log_file_path_movements)

    # --------------
    # Actions
    # --------------
    
    def open_file(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "Open makros", 
            filter="ZIP files (*.zip);;Log files (*.log *.txt);;All files (*)"
        )
        if not fn:
            return
        
        try:
            if fn.lower().endswith('.zip'):
                # Handle ZIP file
                with zipfile.ZipFile(fn, 'r') as zip_file:
                    # Check if required files exist in the ZIP
                    zip_contents = zip_file.namelist()
                    
                    if 'actions.log' not in zip_contents:
                        raise FileNotFoundError("actions.log not found in ZIP file")
                    if 'mouse_moves.log' not in zip_contents:
                        raise FileNotFoundError("mouse_moves.log not found in ZIP file")
                    
                    # Create temporary directory to extract files
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Extract the required files
                        actions_log_path = zip_file.extract('actions.log', temp_dir)
                        mouse_moves_log_path = zip_file.extract('mouse_moves.log', temp_dir)
                        # Load from extracted files
                        self.manager.load_from_file(actions_log_path, mouse_moves_log_path)
                        self._refresh_timeline()
            else:
                # Handle regular log file (keep existing behavior for backward compatibility)
                self.manager.load_from_file(fn, "")
            
            # Refresh the interface
            self.table_model.refresh()
            
            self.status.showMessage(f"Loaded {len(self.manager.events)} events from {os.path.basename(fn)}")
            if self.manager.events:
                self._select_row(0)
            self._update_preview()
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def save_file(self):
        if not self.manager.log_file_path:
            fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save actions.log", filter="Log files (*.log);;All files (*)")
            if not fn:
                return
        else:
            fn = self.manager.log_file_path
        try:
            self.manager.save_to_file(fn)
            self.status.showMessage(f"Saved to {os.path.basename(fn)}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def validate_events(self):
        try:
            ok = self.manager.validate_all_events()
            if ok:
                QtWidgets.QMessageBox.information(self, "Validation", "Events are valid ✔")
            else:
                QtWidgets.QMessageBox.warning(self, "Validation", "Events are invalid ✖")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def _current_real_index_from_table(self) -> Optional[int]:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        proxy_row = sel[0].row()
        return self.table_model.map_to_real_index(proxy_row)

    def add_event(self):
        dlg = EventEditorDialog(self, manager=self.manager)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            vals = dlg.values()
            try:
                # insert after current selection if any
                insert_after = self._current_real_index_from_table()
                insert_index = (insert_after + 1) if insert_after is not None else None
                idx = self.manager.create_event(
                    vals["type"], vals["key"], vals["x"], vals["y"], vals["time"], vals["screenshot"], insert_index=insert_index
                )
                self.table_model.refresh()
                self._refresh_timeline()
                self._select_real_index(idx)
                self.status.showMessage("Event created")
            except ValidationError as ve:
                QtWidgets.QMessageBox.warning(self, "Validation Error", str(ve))
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def edit_event(self):
        real_idx = self._current_real_index_from_table()
        if real_idx is None:
            QtWidgets.QMessageBox.information(self, "Edit Event", "Select an event to edit.")
            return
        ev = self.manager.get_event(real_idx)
        dlg = EventEditorDialog(self, manager=self.manager, event=ev)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            vals = dlg.values()
            try:
                self.manager.modify_event(real_idx, **vals)
                self.table_model.refresh()
                self._refresh_timeline()
                self._select_real_index(real_idx)
                self.status.showMessage("Event updated")
            except ValidationError as ve:
                QtWidgets.QMessageBox.warning(self, "Validation Error", str(ve))
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def delete_event(self):
        real_idx = self._current_real_index_from_table()
        if real_idx is None:
            QtWidgets.QMessageBox.information(self, "Delete Event", "Select an event to delete.")
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete",
            "Delete selected event and its linked pair (if found)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        try:
            deleted = self.manager.delete_event(real_idx)
            self.table_model.refresh()
            self._refresh_timeline()
            # select a nearby row if possible
            next_idx = min(deleted[0], len(self.manager.events) - 1)
            if next_idx >= 0 and self.manager.events:
                self._select_real_index(next_idx)
            else:
                self.table.clearSelection()
            self.status.showMessage(f"Deleted events at indices: {deleted}")
            self._update_preview()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    # --------------
    # Selection + preview
    # --------------
    def _select_row(self, proxy_row: int):
        if proxy_row < 0 or proxy_row >= self.table_model.rowCount():
            return
        sm = self.table.selectionModel()
        self.table.selectRow(proxy_row)
        real_idx = self.table_model.map_to_real_index(proxy_row)
        self._update_preview()

    def _select_real_index(self, real_idx: int):
        proxy_row = self.table_model.map_from_real_index(real_idx)
        if proxy_row is not None:
            self._select_row(proxy_row)
        self._update_preview()

    def _sync_selection_from_table(self):
        real_idx = self._current_real_index_from_table()
        if real_idx is None:
            return
        self._update_preview()

    def _update_preview(self):
        real_idx = self._current_real_index_from_table()
        if real_idx is None:
            self.preview_label.setText("No screenshot")
            self.preview_label.setPixmap(QtGui.QPixmap())
            return
        ev = self.manager.events[real_idx]
        path = resolve_screenshot_path(self.manager.log_file_path, ev.screenshot)
        if path:
            pm = QtGui.QPixmap(path)
            if not pm.isNull():
                self.preview_label.setPixmap(pm.scaled(
                    self.preview_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                ))
                self.preview_label.setText("")
                return
        self.preview_label.setText("No screenshot")
        self.preview_label.setPixmap(QtGui.QPixmap())

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        self._update_preview()

    def _on_filter(self, text: str):
        self.table_model.apply_filter(text)
        # Keep timeline simple (no filtering there), but sync selection if first row exists
        if self.table_model.rowCount() > 0:
            self._select_row(0)
        else:
            self.table.clearSelection()
            self._update_preview()

