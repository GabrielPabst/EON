from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import subprocess
import os
from typing import Optional

from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer, QObject, Signal, Slot
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QStatusBar, QSplitter,
    QSizePolicy, QApplication, QSystemTrayIcon, QMenu, QInputDialog, QDialog,
    QTextEdit, QDialogButtonBox, QStyle, QMessageBox
)

from .widgets.side_nav import SideNav
from .dialogs.import_overlay import ImportOverlay
from .dialogs.record_window import RecordWindow
from .services.macro_store import MacroStore
from .services.replay_service import ReplayService, ReplayError
from .services.hotkey_service import HotkeyService
from .services.recorder_service import RecorderService
from .dialogs.settings_dialog import SettingsDialog


class _UiDispatcher(QObject):
    trigger = Signal(object)
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.trigger.connect(self._on_trigger)
    @Slot(object)
    def _on_trigger(self, fn):
        try:
            print("[UI] dispatcher invoke", flush=True)
            fn()
        except Exception as ex:
            print(f"[UI] dispatcher error: {ex!r}", flush=True)


class MacroDetailsDialog(QDialog):
    def __init__(self, meta: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Macro details")
        self.setMinimumWidth(520)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        name = meta.get("name") or "Unnamed"
        author = meta.get("author") or "Unknown"
        created = meta.get("created_at") or meta.get("downloaded_at") or ""
        counts = meta.get("counts", {})
        desc = meta.get("description") or (meta.get("extra") or {}).get("description") or "No description available."
        root = QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16); root.setSpacing(10)
        title = QLabel(name); title.setObjectName("md_title"); root.addWidget(title)
        meta_line = QLabel(f"Author: {author}    •    Created: {created}"); meta_line.setObjectName("md_meta"); root.addWidget(meta_line)
        if counts:
            cnt = QLabel(f"actions.log: {counts.get('actions.log', 0)}   mouse_moves.log: {counts.get('mouse_moves.log', 0)}")
            cnt.setObjectName("md_meta"); root.addWidget(cnt)
        lab = QLabel("Description"); lab.setObjectName("md_label"); root.addWidget(lab)
        txt = QTextEdit(); txt.setReadOnly(True); txt.setPlainText(desc); root.addWidget(txt, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject); buttons.accepted.connect(self.accept); root.addWidget(buttons)
        self.setStyleSheet("""
        QDialog { background:#0a0a0a; color:#f2f2f2; }
        #md_title { font-size:20px; font-weight:800; margin-bottom:2px; }
        #md_meta { color:#a9abb0; }
        #md_label { color:#9ea0a4; font-size:11px; letter-spacing:.5px; margin-left:2px; }
        QTextEdit { background:#151515; color:#fff; border:1px solid #2b2b2b; border-radius:10px; padding:10px; }
        QDialogButtonBox QPushButton { background:#FFB238; color:#111; border:none; border-radius:8px; padding:8px 14px; font-weight:700; }
        QDialogButtonBox QPushButton:hover { background:#ffc24d; } QDialogButtonBox QPushButton:pressed { background:#e5a831; }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EON – Macro Hub")
        self.resize(1180, 700)

        self.store = MacroStore()
        self._data = self.store.load_all()

        self.replay = ReplayService(self.store)

        self._dispatcher = _UiDispatcher(self)
        self.hotkeys = HotkeyService()
        self.hotkeys.set_ui_dispatcher(lambda fn: self._dispatcher.trigger.emit(fn))
        self.hotkeys.on_start_request = self._hotkey_start_requested
        self.hotkeys.on_stop_request = self._hotkey_stop_requested
        self.hotkeys.set_stop_hotkey("<ctrl>+<shift>+<alt>+s")
        self.hotkeys.start()

        self.recorder = RecorderService(self.store)
        self._record_win: RecordWindow | None = None

        self._poll = QTimer(self); self._poll.setInterval(400); self._poll.timeout.connect(self._poll_replay); self._poll.start()

        quit_action = QAction("Quit", self); quit_action.setShortcut("Ctrl+Q"); quit_action.triggered.connect(QApplication.instance().quit)
        self.addAction(quit_action)

        self._setup_tray()

        self.fs_watcher = None
        try:
            watch_dir = str(self.store.root)
            os.makedirs(watch_dir, exist_ok=True)
            self.fs_watcher = QFileSystemWatcher([watch_dir])
            self.fs_watcher.directoryChanged.connect(self._reload_from_disk)
        except Exception as e:
            self.fs_watcher = None
            if self.statusBar():
                self.statusBar().showMessage(f"Watcher disabled: {e}", 4000)

        root = QWidget(self)
        root_layout = QVBoxLayout(root); root_layout.setContentsMargins(12, 12, 12, 12); root_layout.setSpacing(12)
        self.setCentralWidget(root)

        topbar = QWidget(); tb = QHBoxLayout(topbar); tb.setContentsMargins(0, 0, 0, 0); tb.setSpacing(12)
        def field(lbl: str, w: QWidget) -> QWidget:
            wrap = QWidget(); v = QVBoxLayout(wrap); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(4)
            l = QLabel(lbl); l.setObjectName("fieldLabel"); v.addWidget(l); v.addWidget(w); return wrap
        self.categoryBox = QComboBox(); self.categoryBox.addItems(["All", "Office", "Audio", "Video", "Utilities"]); self.categoryBox.setMinimumWidth(160)
        self.authorEdit = QLineEdit(); self.authorEdit.setPlaceholderText("Author…"); self.authorEdit.setMinimumWidth(180)
        self.timeBox = QComboBox(); self.timeBox.addItems(["All", "Today", "Last 7 days", "Last month", "Last 3 months"]); self.timeBox.setMinimumWidth(190)
        tb.addWidget(field("Category", self.categoryBox))
        tb.addWidget(field("Author", self.authorEdit))
        tb.addWidget(field("Download time", self.timeBox))
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); tb.addWidget(spacer, 1)
        self.searchEdit = QLineEdit(); self.searchEdit.setPlaceholderText("Search…"); self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setMinimumHeight(38); self.searchEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); tb.addWidget(self.searchEdit, 2)
        self.btnRecord = QPushButton("Record"); self.btnRecord.setMinimumHeight(38); self.btnRecord.clicked.connect(self._open_record_window); tb.addWidget(self.btnRecord)
        root_layout.addWidget(topbar)

        split = QSplitter(Qt.Horizontal, self)

        list_container = QWidget()
        lv = QVBoxLayout(list_container); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(10)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Description", "Action", "Hotkey"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 420)
        self.table.setColumnWidth(3, 220)

        lv.addWidget(self.table, 1)

        self.side = SideNav()
        self.side.requestImport.connect(self._open_import_overlay)
        self.side.requestSettings.connect(self._open_settings_dialog)

        split.addWidget(list_container); split.addWidget(self.side)
        split.setStretchFactor(0, 1); split.setStretchFactor(1, 0)
        root_layout.addWidget(split, 1)

        self.setStatusBar(QStatusBar())

        self.searchEdit.textChanged.connect(self._refresh_table)
        self.categoryBox.currentIndexChanged.connect(self._refresh_table)
        self.authorEdit.textChanged.connect(self._refresh_table)
        self.timeBox.currentIndexChanged.connect(self._refresh_table)

        self._apply_styles()
        self._refresh_table()

    def _open_record_window(self):
        try:
            if self._record_win and self._record_win.isVisible():
                self._record_win.raise_(); self._record_win.activateWindow(); return
        except RuntimeError:
            self._record_win = None
        self._record_win = RecordWindow(self.recorder, parent=self)
        self._record_win.saved.connect(self._on_record_saved)
        self._record_win.canceled.connect(lambda: None)
        self._record_win.show(); self._record_win.raise_(); self._record_win.activateWindow()

    def _on_record_saved(self, meta: dict):
        try:
            mid = meta.get("id")
            if mid:
                for i, row in enumerate(self._data):
                    if row.get("id") == mid:
                        merged = dict(row); merged.update(meta or {})
                        self._data[i] = merged
                        break
                else:
                    self._data.insert(0, meta)
            else:
                self._data = self.store.load_all()
        except Exception:
            self._data = self.store.load_all()
        self._refresh_table()
        name = meta.get("name") or "New macro"
        self.statusBar().showMessage(f"Saved recording: {name}", 3000)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None; return
        self.tray = QSystemTrayIcon(self)
        std_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray.setIcon(std_icon)
        menu = QMenu()
        act_show = QAction("Open", self); act_show.triggered.connect(self._restore_from_taskbar_or_tray)
        act_quit = QAction("Quit", self); act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_show); menu.addSeparator(); menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.setToolTip("EON – Macro Hub")
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restore_from_taskbar_or_tray()

    def _minimize(self):
        self.showMinimized()

    def _restore_from_taskbar_or_tray(self):
        self.showNormal(); self.raise_(); self.activateWindow()

    def _open_import_overlay(self):
        dlg = ImportOverlay(self)
        dlg.move(self.geometry().center() - dlg.rect().center())
        if dlg.exec() != QDialog.Accepted:
            self.statusBar().showMessage("Import canceled.", 1800); return
        if not dlg.selected_path:
            self.statusBar().showMessage("No path selected.", 2000); return
        try:
            kind = dlg.selected_kind
            if kind == "zip":
                meta = self.store.add_from_zip(dlg.selected_path)
            elif kind == "folder":
                meta = self.store.add_from_folder(dlg.selected_path)
            else:
                raise ValueError("Only ZIP or folder are supported.")
            self._data.insert(0, meta)
            self._refresh_table()
            counts = meta.get("counts", {})
            a = counts.get("actions.log", 0); m = counts.get("mouse_moves.log", 0)
            self.statusBar().showMessage(f"Imported: {meta['name']}  (actions: {a} / moves: {m})", 3500)
        except Exception as ex:
            self.statusBar().showMessage(f"Import failed: {ex}", 5000)

    def _reload_from_disk(self):
        self._data = self.store.load_all()
        self._refresh_table()

    def _row_desc(self, row: dict) -> str:
        return row.get("description") or (row.get("extra") or {}).get("description") or ""

    def _format_hotkey_display(self, val: Optional[str]) -> str:
        if not val:
            return "Set hotkey"
        s = str(val).strip()
        if len(s) == 1:
            return f"Ctrl+Shift+Alt+{s.upper()}"
        return s

    def _passes_filters(self, row: dict) -> bool:
        if (c := self.categoryBox.currentText()) != "All" and row.get("category") != c:
            return False
        a = self.authorEdit.text().strip().lower()
        if a and a not in (row.get("author", "") or "").lower():
            return False
        sel = self.timeBox.currentText()
        if sel != "All":
            limits = {"Today": 1, "Last 7 days": 7, "Last month": 31, "Last 3 months": 93}
            limit_days = limits.get(sel)
            if limit_days is not None:
                try:
                    dt = datetime.fromisoformat((row.get("downloaded_at", "") or "").replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - dt).days
                    if age_days > limit_days:
                        return False
                except Exception:
                    return False
        q = self.searchEdit.text().strip().lower()
        if q:
            if q in (row.get("name", "") or "").lower():
                return True
            if q in self._row_desc(row).lower():
                return True
            return False
        return True

    def _make_desc_cell(self, row: dict) -> QWidget:
        desc = self._row_desc(row).strip() or "No description"
        short = (desc[:117].rstrip() + "…") if len(desc) > 120 else desc
        btn = QPushButton(short); btn.setToolTip("Show details"); btn.setObjectName("descChip"); btn.setFlat(True); btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _, r=row: self._show_details(r))
        wrap = QWidget(); h = QHBoxLayout(wrap); h.setContentsMargins(6, 6, 6, 6); h.setSpacing(0); h.addWidget(btn)
        return wrap

    def _show_details(self, row: dict):
        dlg = MacroDetailsDialog(row, self)
        dlg.move(self.geometry().center() - dlg.rect().center())
        dlg.exec()

    def _refresh_table(self):
        rows = [r for r in self._data if self._passes_filters(r)]
        self.table.setRowCount(len(rows))
        name_font = QFont(); name_font.setPointSize(15); name_font.setWeight(QFont.Medium)

        for r, row in enumerate(rows):
            item = QTableWidgetItem(row.get("name") or "Unnamed")
            item.setFont(name_font)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
            self.table.setItem(r, 0, item)

            self.table.setCellWidget(r, 1, self._make_desc_cell(row))

            btnEdit = QPushButton("Edit")
            btnPlay = QPushButton("Play")
            btnFolder = QPushButton("Open folder")
            btnDelete = QPushButton("Delete")
            for b in (btnEdit, btnPlay, btnFolder, btnDelete):
                b.setProperty("cellAction", True)
                b.setMinimumHeight(36)
                b.setMinimumWidth(96)
                b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btnEdit.clicked.connect(lambda _, id=row["id"]: self._open_action_editor(id))
            btnPlay.clicked.connect(lambda _, id=row["id"]: self._play_macro(id))
            btnFolder.clicked.connect(lambda _, id=row["id"]: self._open_folder(id))
            btnDelete.clicked.connect(lambda _, id=row["id"]: self._delete_macro(id))
            container = QWidget()
            hl = QHBoxLayout(container); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(10)
            hl.addStretch(1); hl.addWidget(btnEdit); hl.addWidget(btnPlay); hl.addWidget(btnFolder); hl.addWidget(btnDelete); hl.addStretch(1)
            self.table.setCellWidget(r, 2, container)

            hk_text = self._format_hotkey_display(row.get("hotkey"))
            hk_btn = QPushButton(hk_text); hk_btn.setMinimumHeight(36)
            hk_btn.clicked.connect(lambda _, id=row["id"]: self._set_hotkey_for(id))
            hk_wrap = QWidget(); hk_l = QHBoxLayout(hk_wrap); hk_l.setContentsMargins(0, 0, 0, 0); hk_l.setSpacing(0)
            hk_l.addStretch(1); hk_l.addWidget(hk_btn, 0, Qt.AlignCenter); hk_l.addStretch(1)
            self.table.setCellWidget(r, 3, hk_wrap)

            self.table.setRowHeight(r, 56)

        self.table.setColumnWidth(2, 420); self.table.setColumnWidth(3, 220)
        self._sync_hotkeys(rows)

    def _ensure_editor_on_path(self) -> Path:
        desktop_root = Path(__file__).resolve().parents[2]
        viewer_dir = desktop_root / "MakroTimelineViewer"
        if str(viewer_dir) not in sys.path:
            sys.path.insert(0, str(viewer_dir))
        return viewer_dir

    def _open_action_editor(self, macro_id: str):
        macro_dir = Path(self.store.dir_for(macro_id))
        actions_path = macro_dir / "actions.log"
        actions_fixed_path = macro_dir / "actions.fixed.log"
        moves_path = macro_dir / "mouse_moves.log"
        if not actions_path.exists() and not actions_fixed_path.exists():
            self.statusBar().showMessage("No actions log found in macro folder.", 3500); return
        actions_to_open = actions_fixed_path if actions_fixed_path.exists() else actions_path

        self._ensure_editor_on_path()
        try:
            from action_log_frontend import ActionLogFrontend  # type: ignore
        except Exception as e:
            self.statusBar().showMessage(f"Editor import failed: {e}", 5000); return

        try:
            win = ActionLogFrontend()
            old_cwd = os.getcwd()
            try:
                os.chdir(str(macro_dir))
            except Exception:
                old_cwd = None
            if old_cwd is not None:
                try:
                    win.destroyed.connect(lambda *_: self._restore_cwd_safe(old_cwd))
                except Exception:
                    pass

            sroot = str((macro_dir / "screenshots").resolve())
            try:
                if hasattr(win, "set_screenshot_root") and callable(getattr(win, "set_screenshot_root")):
                    win.set_screenshot_root(sroot)
                elif hasattr(win, "manager"):
                    mgr = getattr(win, "manager", None)
                    if mgr is not None:
                        if hasattr(mgr, "set_screenshot_root") and callable(getattr(mgr, "set_screenshot_root")):
                            mgr.set_screenshot_root(sroot)
                        else:
                            try: setattr(mgr, "screenshot_root", sroot)
                            except Exception: pass
                        try:
                            def _resolve_screenshot(p: str) -> str:
                                from pathlib import Path as _P
                                pth = _P(p)
                                return str((macro_dir / pth).resolve()) if not pth.is_absolute() else str(pth)
                            setattr(mgr, "resolve_screenshot_path", _resolve_screenshot)
                        except Exception: pass
            except Exception:
                pass

            try:
                win.manager.load_from_file(str(actions_to_open), str(moves_path if moves_path.exists() else ""))
            except Exception as load_err:
                self.statusBar().showMessage(f"Loaded editor, but failed to load logs: {load_err}", 6000)

            if hasattr(win, "table_model"):
                try: win.table_model.refresh()
                except Exception: pass
            if hasattr(win, "_refresh_timeline"):
                try: win._refresh_timeline()
                except Exception: pass
            try:
                if getattr(win.manager, "events", None):
                    if hasattr(win, "_select_row") and callable(getattr(win, "_select_row")):
                        win._select_row(0)
                    elif hasattr(win, "table_view"):
                        win.table_view.selectRow(0)
                if hasattr(win, "_update_preview"):
                    win._update_preview()
            except Exception:
                pass

            if not hasattr(self, "_editor_windows"):
                self._editor_windows = []
            self._editor_windows.append(win)
            win.show()
        except Exception as e:
            try:
                if 'old_cwd' in locals() and old_cwd is not None:
                    self._restore_cwd_safe(old_cwd)
            except Exception:
                pass
            self.statusBar().showMessage(f"Failed to open editor: {e}", 6000)

    def _restore_cwd_safe(self, old_cwd: str):
        try:
            os.chdir(old_cwd)
        except Exception:
            pass

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.statusBar().showMessage("Settings saved.", 2000)

    def _sync_hotkeys(self, rows):
        for row in rows:
            self.hotkeys.set_macro_hotkey(row["id"], row.get("hotkey"))

    def _set_hotkey_for(self, macro_id: str):
        current = self._find_meta(macro_id).get("hotkey") or ""
        text, ok = QInputDialog.getText(
            self, "Set hotkey",
            "Letter (a–z). It will trigger with Ctrl+Shift+Alt+<letter>.\n"
            "Leave empty to remove:", text=current,
        )
        if not ok:
            return
        letter = (text or "").strip().lower()
        if letter == "":
            normalized: Optional[str] = None
        else:
            if len(letter) != 1 or not letter.isalpha():
                self.statusBar().showMessage("Please enter exactly one letter (a–z).", 3000); return
            if letter == "s":
                self.statusBar().showMessage("Letter 's' is reserved for Stop (Ctrl+Shift+Alt+S).", 4000); return
            normalized = letter
        try:
            meta = self.store.set_hotkey(macro_id, normalized)
            for i, row in enumerate(self._data):
                if row["id"] == macro_id:
                    self._data[i] = meta
                    break
            self._refresh_table()
            shown = "removed" if not normalized else f"set to Ctrl+Shift+Alt+{normalized.upper()}"
            self.statusBar().showMessage(f"Hotkey {shown}.", 2500)
        except Exception as e:
            self.statusBar().showMessage(f"Hotkey error: {e}", 4000)

    def _find_meta(self, macro_id: str) -> dict:
        for r in self._data:
            if r["id"] == macro_id:
                return r
        return {}

    def _delete_macro(self, macro_id: str):
        meta = self._find_meta(macro_id)
        name = meta.get("name") if meta else macro_id
        box = QMessageBox(self)
        box.setWindowTitle("Delete macro")
        box.setText(f"Delete '{name}'?\nThis macro will be removed from Macro Hub and its files moved to the Trash.")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        if box.exec() != QMessageBox.Yes:
            return
        try:
            try:
                self.replay.stop_replay()
            except Exception:
                pass
            self.store.delete_macro(macro_id)
            self._data = [r for r in self._data if r.get("id") != macro_id]
            self._refresh_table()
            self.statusBar().showMessage(f"Deleted: {name}", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Delete failed: {e}", 5000)

    def _hotkey_start_requested(self, macro_id: str):
        print(f"[UI] hotkey_start_requested({macro_id})", flush=True)
        self._play_macro(macro_id)

    def _hotkey_stop_requested(self):
        print("[UI] hotkey_stop_requested()", flush=True)
        try:
            self.replay.stop_replay()
            self.statusBar().showMessage("Replay stopped (hotkey).", 2000)
        except Exception as ex:
            self.statusBar().showMessage(f"Stop failed: {ex}", 2000)

    def _poll_replay(self):
        err = self.replay.poll_finish()
        if err is not None:
            if err:
                self.statusBar().showMessage(err, 5000)
            else:
                self.statusBar().showMessage("Replay finished.", 2500)

    def _play_macro(self, macro_id: str):
        print(f"[UI] _play_macro called: macro_id={macro_id}", flush=True)
        try:
            self.replay.start_replay(macro_id)
            self.statusBar().showMessage("Replay started. (Stop: Ctrl+Shift+Alt+S)", 4000)
            self._minimize()
        except ReplayError as e:
            self.statusBar().showMessage(f"Replay error: {e}", 6000)
        except Exception as e:
            self.statusBar().showMessage(f"Failed to start replay: {e}", 6000)

    def _open_folder(self, macro_id: str):
        target = Path(self.store.dir_for(macro_id))
        chosen: Optional[Path] = target
        try:
            if not target.exists():
                found = self.store.find_existing_dir(macro_id) if hasattr(self.store, "find_existing_dir") else None
                if found:
                    chosen = Path(found)
        except Exception:
            pass
        if chosen is None or not chosen.exists():
            chosen = Path(self.store.root)
        try:
            chosen.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.statusBar().showMessage(f"Could not ensure directory: {chosen}", 4000)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(chosen))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(chosen)])
            else:
                subprocess.Popen(["xdg-open", str(chosen)])
            self.statusBar().showMessage(f"Opened folder: {chosen}", 2500)
        except Exception as e:
            self.statusBar().showMessage(f"Could not open folder: {e}", 4000)

    def _apply_styles(self):
        self.setStyleSheet("""
        QMainWindow { background:#0a0a0a; color:#f2f2f2; }
        #fieldLabel { color:#9ea0a4; font-size:11px; letter-spacing:.5px; margin-left:4px; margin-bottom:2px; }
        QLineEdit, QComboBox { background:#151515; color:#fff; border:1px solid #2b2b2b; border-radius:10px; padding:8px 12px; }
        QLineEdit:hover, QComboBox:hover { border-color:#3a3a3a; }
        QComboBox::drop-down { border:0; }
        QComboBox QAbstractItemView { background:#151515; color:#fff; selection-background-color:#ffbe44; selection-color:#111; }
        QPushButton { background:#FFB238; color:#111; border:none; border-radius:8px; padding:8px 14px; font-weight:600; }
        QPushButton:hover { background:#ffc24d; } QPushButton:pressed { background:#e5a831; }
        QTableWidget { background:#0f0f0f; color:#eaeaea; alternate-background-color:#101010; border:1px solid #242424; border-radius:8px; }
        QHeaderView::section { background:#121212; color:#bfbfbf; border:0; padding:12px; font-weight:600; border-bottom:2px solid #FFB238; }
        QTableWidget::item:hover { background: rgba(255, 187, 80, 0.16); }
        QTableWidget::item:selected { background: rgba(255, 187, 80, 0.26); color:#fff; }
        #descChip { background: rgba(255, 187, 80, 0.13); color:#ffcf73; border:1px solid rgba(255, 187, 80, 0.35);
                    border-radius:10px; padding:8px 10px; font-weight:600; text-align:left; }
        #descChip:hover { background: rgba(255, 187, 80, 0.2); }
        """)
