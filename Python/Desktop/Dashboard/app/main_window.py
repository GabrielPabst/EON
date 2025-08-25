# app/main_window.py
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import subprocess

from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import QStyle
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QComboBox, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QStatusBar, QSplitter, QSizePolicy, QApplication,
    QSystemTrayIcon, QMenu, QInputDialog
)

from .widgets.side_nav import SideNav
from .dialogs.import_overlay import ImportOverlay
from .services.macro_store import MacroStore
from .services.replay_service import ReplayService, ReplayError
from .services.hotkey_service import HotkeyService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EON – Macro Hub")
        self.resize(1180, 700)

        # Data store
        self.store = MacroStore()
        self._data = self.store.load_all()

        # Replay + hotkeys
        self.replay = ReplayService(self.store)
        self.hotkeys = HotkeyService()
        self.hotkeys.on_start_request = lambda macro_id: QTimer.singleShot(
            0, lambda m=macro_id: self._hotkey_start_requested(m)
        )
        self.hotkeys.on_stop_request = lambda: QTimer.singleShot(0, self._hotkey_stop_requested)
        self.hotkeys.start()
        self.hotkeys.set_stop_hotkey("<ctrl>+<alt>+s")

        # Poll subprocess finish
        self._poll = QTimer(self)
        self._poll.setInterval(400)
        self._poll.timeout.connect(self._poll_replay)
        self._poll.start()

        # Ctrl+Q to quit
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(QApplication.instance().quit)
        self.addAction(quit_action)

        # Tray (optional)
        self._setup_tray()

        # Watcher
        self.fs_watcher = QFileSystemWatcher([self.store.root])
        self.fs_watcher.directoryChanged.connect(self._reload_from_disk)

        # Root
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        # Topbar
        topbar = QWidget()
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(12)

        def field(lbl: str, w: QWidget) -> QWidget:
            wrap = QWidget()
            v = QVBoxLayout(wrap)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)
            l = QLabel(lbl)
            l.setObjectName("fieldLabel")
            v.addWidget(l)
            v.addWidget(w)
            return wrap

        self.categoryBox = QComboBox()
        self.categoryBox.addItems(["All", "Office", "Audio", "Video", "Utilities"])
        self.categoryBox.setMinimumWidth(160)

        self.authorEdit = QLineEdit()
        self.authorEdit.setPlaceholderText("Author…")
        self.authorEdit.setMinimumWidth(180)

        self.timeBox = QComboBox()
        self.timeBox.addItems(["All", "Today", "Last 7 days", "Last month", "Last 3 months"])
        self.timeBox.setMinimumWidth(190)

        tb.addWidget(field("Category", self.categoryBox))
        tb.addWidget(field("Author", self.authorEdit))
        tb.addWidget(field("Download time", self.timeBox))

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tb.addWidget(spacer, 1)

        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Search…")
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setMinimumHeight(38)
        self.searchEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tb.addWidget(self.searchEdit, 2)

        root_layout.addWidget(topbar)

        # Splitter
        split = QSplitter(Qt.Horizontal, self)

        # Table
        list_container = QWidget()
        lv = QVBoxLayout(list_container)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Action", "Hotkey"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 320)  # more room for 3 buttons
        self.table.setColumnWidth(2, 220)

        lv.addWidget(self.table, 1)

        # Side nav
        self.side = SideNav()
        self.side.requestImport.connect(self._open_import_overlay)

        split.addWidget(list_container)
        split.addWidget(self.side)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        root_layout.addWidget(split, 1)

        # Statusbar
        self.setStatusBar(QStatusBar())

        # Filter wiring
        self.searchEdit.textChanged.connect(self._refresh_table)
        self.categoryBox.currentIndexChanged.connect(self._refresh_table)
        self.authorEdit.textChanged.connect(self._refresh_table)
        self.timeBox.currentIndexChanged.connect(self._refresh_table)

        # Styles + initial data
        self._apply_styles()
        self._refresh_table()

    # ---------- Tray ----------
    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self)
        std_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray.setIcon(std_icon)
        menu = QMenu()
        act_show = QAction("Open", self)
        act_show.triggered.connect(self._restore_from_taskbar_or_tray)
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.setToolTip("EON – Macro Hub")
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restore_from_taskbar_or_tray()

    def _minimize(self):
        """Minimize to taskbar (do not hide/quit)."""
        self.showMinimized()

    def _restore_from_taskbar_or_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ---------- Import ----------
    def _open_import_overlay(self):
        dlg = ImportOverlay(self)
        dlg.move(self.geometry().center() - dlg.rect().center())

        if dlg.exec() != QDialog.Accepted:
            self.statusBar().showMessage("Import canceled.", 1800)
            return

        if not dlg.selected_path:
            self.statusBar().showMessage("No path selected.", 2000)
            return

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
            a = counts.get("actions.log", 0)
            m = counts.get("mouse_moves.log", 0)
            self.statusBar().showMessage(f"Imported: {meta['name']}  (actions: {a} / moves: {m})", 3500)
        except Exception as ex:
            self.statusBar().showMessage(f"Import failed: {ex}", 5000)

    # ---------- Watcher / Reload ----------
    def _reload_from_disk(self):
        self._data = self.store.load_all()
        self._refresh_table()

    # ---------- Table / Filters ----------
    def _passes_filters(self, row: dict) -> bool:
        if (c := self.categoryBox.currentText()) != "All" and row.get("category") != c:
            return False
        a = self.authorEdit.text().strip().lower()
        if a and a not in row.get("author", "").lower():
            return False
        sel = self.timeBox.currentText()
        if sel != "All":
            limits = {"Today": 1, "Last 7 days": 7, "Last month": 31, "Last 3 months": 93}
            limit_days = limits.get(sel)
            if limit_days is not None:
                try:
                    dt = datetime.fromisoformat(row.get("downloaded_at", "").replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - dt).days
                    if age_days > limit_days:
                        return False
                except Exception:
                    return False
        q = self.searchEdit.text().strip().lower()
        if q and q not in row.get("name", "").lower():
            return False
        return True

    def _refresh_table(self):
        rows = [r for r in self._data if self._passes_filters(r)]
        self.table.setRowCount(len(rows))

        name_font = QFont()
        name_font.setPointSize(15)
        name_font.setWeight(QFont.Medium)

        for r, row in enumerate(rows):
            # Name
            item = QTableWidgetItem(row["name"])
            item.setFont(name_font)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
            self.table.setItem(r, 0, item)

            # === Actions: Edit | Play | Open folder ===
            btnEdit = QPushButton("Edit")
            btnPlay = QPushButton("Play")
            btnFolder = QPushButton("Open folder")

            for b in (btnEdit, btnPlay, btnFolder):
                b.setProperty("cellAction", True)
                b.setMinimumHeight(36)
                b.setMinimumWidth(96)
                b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            btnEdit.clicked.connect(lambda _, id=row["id"]: self._open_action_editor(id))
            btnPlay.clicked.connect(lambda _, id=row["id"]: self._play_macro(id))
            btnFolder.clicked.connect(lambda _, id=row["id"]: self._open_folder(id))

            container = QWidget()
            hl = QHBoxLayout(container)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(10)  # even gaps
            hl.addStretch(1)
            hl.addWidget(btnEdit)
            hl.addWidget(btnPlay)
            hl.addWidget(btnFolder)
            hl.addStretch(1)
            self.table.setCellWidget(r, 1, container)

            # Hotkey: view / set
            hk_btn = QPushButton(row.get("hotkey") or "Set hotkey")
            hk_btn.setMinimumHeight(36)
            hk_btn.clicked.connect(lambda _, id=row["id"]: self._set_hotkey_for(id))
            hk_wrap = QWidget()
            hk_l = QHBoxLayout(hk_wrap)
            hk_l.setContentsMargins(0, 0, 0, 0)
            hk_l.setSpacing(0)
            hk_l.addStretch(1)
            hk_l.addWidget(hk_btn, 0, Qt.AlignCenter)
            hk_l.addStretch(1)
            self.table.setCellWidget(r, 2, hk_wrap)

            self.table.setRowHeight(r, 56)

        self.table.setColumnWidth(1, 320)
        self.table.setColumnWidth(2, 220)
        self._sync_hotkeys(rows)

    # ---------- Open Action Log Frontend ----------
    def _ensure_editor_on_path(self) -> Path:
        """Ensure .../Desktop/MakroTimelineViewer is on sys.path."""
        desktop_root = Path(__file__).resolve().parents[2]  # .../Desktop
        viewer_dir = desktop_root / "MakroTimelineViewer"
        if str(viewer_dir) not in sys.path:
            sys.path.insert(0, str(viewer_dir))
        return viewer_dir

    def _open_action_editor(self, macro_id: str):
        macro_dir = Path(self.store.dir_for(macro_id))
        actions_path = macro_dir / "actions.log"
        moves_path = macro_dir / "mouse_moves.log"

        if not actions_path.exists():
            self.statusBar().showMessage("No actions.log found in macro folder.", 3500)
            return

        viewer_dir = self._ensure_editor_on_path()
        try:
            from action_log_frontend import ActionLogFrontend  # type: ignore
        except Exception as e:
            self.statusBar().showMessage(f"Editor import failed: {e}", 5000)
            return

        try:
            win = ActionLogFrontend()
            try:
                win.manager.load_from_file(str(actions_path), str(moves_path if moves_path.exists() else ""))
                if hasattr(win, "table_model"):
                    win.table_model.refresh()
                if hasattr(win, "_refresh_timeline"):
                    try:
                        win._refresh_timeline()
                    except Exception:
                        pass
            except Exception as load_err:
                self.statusBar().showMessage(f"Loaded editor, but failed to load logs: {load_err}", 6000)

            if not hasattr(self, "_editor_windows"):
                self._editor_windows = []
            self._editor_windows.append(win)
            win.show()
        except Exception as e:
            self.statusBar().showMessage(f"Failed to open editor: {e}", 6000)

    # ---------- Hotkeys ----------
    def _sync_hotkeys(self, rows):
        for row in rows:
            self.hotkeys.set_macro_hotkey(row["id"], row.get("hotkey"))

    def _set_hotkey_for(self, macro_id: str):
        text, ok = QInputDialog.getText(
            self, "Set hotkey",
            "Hotkey (e.g. <ctrl>+<alt>+p). Leave empty to remove:",
            text=self._find_meta(macro_id).get("hotkey") or "",
        )
        if not ok:
            return
        text = (text.strip() or None)
        try:
            meta = self.store.set_hotkey(macro_id, text)
            for i, row in enumerate(self._data):
                if row["id"] == macro_id:
                    self._data[i] = meta
                    break
            self._refresh_table()
            self.statusBar().showMessage("Hotkey updated.", 2000)
        except Exception as e:
            self.statusBar().showMessage(f"Hotkey error: {e}", 4000)

    def _find_meta(self, macro_id: str) -> dict:
        for r in self._data:
            if r["id"] == macro_id:
                return r
        return {}

    def _hotkey_start_requested(self, macro_id: str):
        self._minimize()
        self._play_macro(macro_id)

    def _hotkey_stop_requested(self):
        try:
            self.replay.stop_replay()
            self.statusBar().showMessage("Replay stopped (hotkey).", 2000)
        except Exception:
            pass

    def _poll_replay(self):
        err = self.replay.poll_finish()
        if err is not None:
            if err:
                self.statusBar().showMessage(err, 5000)
            else:
                self.statusBar().showMessage("Replay finished.", 2500)

    # ---------- Replay ----------
    def _play_macro(self, macro_id: str):
        try:
            self.replay.start_replay(macro_id)
            self.statusBar().showMessage("Replay started. (Stop: Ctrl+Alt+S)", 4000)
            self._minimize()
        except ReplayError as e:
            self.statusBar().showMessage(f"Replay error: {e}", 6000)
        except Exception as e:
            self.statusBar().showMessage(f"Failed to start replay: {e}", 6000)

    # ---------- Open macro folder ----------
    def _open_folder(self, macro_id: str):
        path = Path(self.store.dir_for(macro_id))
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.statusBar().showMessage(f"Could not open folder: {e}", 4000)

    # ---------- Styles ----------
    def _apply_styles(self):
        self.setStyleSheet("""
        QMainWindow { background:#0a0a0a; color:#f2f2f2; }
        #fieldLabel { color:#9ea0a4; font-size:11px; letter-spacing:.5px; margin-left:4px; margin-bottom:2px; }
        QLineEdit, QComboBox { background:#151515; color:#fff; border:1px solid #2b2b2b; border-radius:10px; padding:8px 12px; }
        QLineEdit:hover, QComboBox:hover { border-color:#3a3a3a; }
        QComboBox::drop-down { border:0; }
        QComboBox QAbstractItemView { background:#151515; color:#fff; selection-background-color:#ffbe44; selection-color:#111; }
        QPushButton { background:#FFB238; color:#111; border:none; border-radius:8px; padding:8px 14px; font-weight:600; }
        QPushButton:hover { background:#ffc24d; }
        QPushButton:pressed { background:#e5a831; }
        QTableWidget { background:#0f0f0f; color:#eaeaea; alternate-background-color:#101010; border:1px solid #242424; border-radius:8px; }
        QHeaderView::section { background:#121212; color:#bfbfbf; border:0; padding:12px; font-weight:600; border-bottom:2px solid #FFB238; }
        QTableWidget::item:hover { background: rgba(255, 187, 80, 0.16); }
        QTableWidget::item:selected { background: rgba(255, 187, 80, 0.26); color:#fff; }
        """)
