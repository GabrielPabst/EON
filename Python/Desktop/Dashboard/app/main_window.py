# app/main_window.py
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import subprocess

from PySide6.QtCore import Qt, QFileSystemWatcher
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QComboBox, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QStatusBar, QSplitter, QSizePolicy, QDialog
)

from .widgets.side_nav import SideNav
from .dialogs.import_overlay import ImportOverlay
from .services.macro_store import MacroStore


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EON – Macro Hub")
        self.resize(1180, 700)

        # Datenhaltung
        self.store = MacroStore()
        self._data = self.store.load_all()

        # Watcher: wenn sich etwas im Makro-Ordner ändert -> neu laden
        self.fs_watcher = QFileSystemWatcher([self.store.root])
        self.fs_watcher.directoryChanged.connect(self._reload_from_disk)

        # Root
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        # Topbar (Filter + Suche)
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
        self.categoryBox.addItems(["Alle", "Office", "Audio", "Video", "Utilities"])
        self.categoryBox.setMinimumWidth(160)

        self.authorEdit = QLineEdit()
        self.authorEdit.setPlaceholderText("Autor…")
        self.authorEdit.setMinimumWidth(180)

        self.timeBox = QComboBox()
        self.timeBox.addItems(["Alle", "Heute", "Letzte 7 Tage", "Letzter Monat", "Letzte 3 Monate"])
        self.timeBox.setMinimumWidth(190)

        tb.addWidget(field("Kategorie", self.categoryBox))
        tb.addWidget(field("Autor", self.authorEdit))
        tb.addWidget(field("Download-Zeit", self.timeBox))

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tb.addWidget(spacer, 1)

        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Suchen…")
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setMinimumHeight(38)
        self.searchEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tb.addWidget(self.searchEdit, 2)

        root_layout.addWidget(topbar)

        # Splitter: Liste | SideNav
        split = QSplitter(Qt.Horizontal, self)

        # Liste (Tabelle)
        list_container = QWidget()
        lv = QVBoxLayout(list_container)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Aktion"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)  # damit Hover ohne Klick klappt

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 150)

        lv.addWidget(self.table, 1)

        # Side-Navbar
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

        # Styles + Daten initial
        self._apply_styles()
        self._refresh_table()

    # ---------- Import ----------
    def _open_import_overlay(self):
        dlg = ImportOverlay(self)
        # Sicher zentriert anzeigen (Dialog macht das auch in showEvent)
        dlg.move(self.geometry().center() - dlg.rect().center())

        if dlg.exec() != QDialog.Accepted:
            self.statusBar().showMessage("Import abgebrochen.", 1800)
            return

        if not dlg.file_path:
            self.statusBar().showMessage("Keine Datei ausgewählt.", 2000)
            return

        try:
            meta = self.store.add_from_file(dlg.file_path)
            self._data.insert(0, meta)
            self._refresh_table()
            self.statusBar().showMessage(
                f"Importiert: {meta['name']}  ({meta['counts']['lines']} Zeilen)", 3000
            )
        except Exception as ex:
            self.statusBar().showMessage(f"Import fehlgeschlagen: {ex}", 4000)

    # ---------- Watcher / Reload ----------
    def _reload_from_disk(self):
        self._data = self.store.load_all()
        self._refresh_table()

    # ---------- Tabelle / Filter ----------
    def _passes_filters(self, row: dict) -> bool:
        # Kategorie
        if (c := self.categoryBox.currentText()) != "Alle" and row.get("category") != c:
            return False

        # Autor
        a = self.authorEdit.text().strip().lower()
        if a and a not in row.get("author", "").lower():
            return False

        # Download-Zeit anhand downloaded_at (ISO, UTC)
        sel = self.timeBox.currentText()
        if sel != "Alle":
            limits = {"Heute": 1, "Letzte 7 Tage": 7, "Letzter Monat": 31, "Letzte 3 Monate": 93}
            limit_days = limits.get(sel)
            if limit_days is not None:
                try:
                    dt = datetime.fromisoformat(row.get("downloaded_at", "").replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - dt).days
                    if age_days > limit_days:
                        return False
                except Exception:
                    # Wenn Datum unbrauchbar ist, lieber ausblenden
                    return False

        # Volltextsuche
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
            # Name als nicht editierbares / nicht selektierbares Item
            item = QTableWidgetItem(row["name"])
            item.setFont(name_font)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
            self.table.setItem(r, 0, item)

            # Bearbeiten -> Timeline öffnen
            btn = QPushButton("Bearbeiten")
            btn.setProperty("cellAction", True)
            btn.setMinimumHeight(36)
            btn.setMinimumWidth(120)
            btn.clicked.connect(lambda _, id=row["id"]: self._open_macro_timeline(id))

            container = QWidget()
            hl = QHBoxLayout(container)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addStretch(1)
            hl.addWidget(btn, 0, Qt.AlignCenter)
            hl.addStretch(1)
            self.table.setCellWidget(r, 1, container)

            self.table.setRowHeight(r, 56)

        self.table.setColumnWidth(1, 150)

    # ---------- Timeline Viewer öffnen ----------
    def _ensure_timeline_on_path(self) -> Path:
        """
        Fügt den Ordner 'MakroTimelineViewer' (neben 'Dashboard') zu sys.path hinzu
        und gibt den Pfad zurück.
        Erwartete Struktur:
          Desktop/
            Dashboard/
            MakroTimelineViewer/
        """
        # .../Dashboard/app/main_window.py -> .../Desktop
        desktop_root = Path(__file__).resolve().parents[2]
        viewer_dir = desktop_root / "MakroTimelineViewer"
        if str(viewer_dir) not in sys.path:
            sys.path.insert(0, str(viewer_dir))
        return viewer_dir

    def _open_macro_timeline(self, macro_id: str):
        """
        Öffnet das Timeline-Fenster und lädt actions.log/mouse_moves.log
        des gewählten Makros. Zuerst In-Process, sonst als separater Prozess.
        """
        macro_dir = Path(self.store.dir_for(macro_id))
        actions_path = macro_dir / "actions.log"
        mouse_path   = macro_dir / "mouse_moves.log"

        if not actions_path.exists() and not mouse_path.exists():
            self.statusBar().showMessage("Keine Logs gefunden (actions.log / mouse_moves.log).", 3000)
            return

        viewer_dir = self._ensure_timeline_on_path()

        # Versuch 1: In-Process importieren (schönes neues Fenster innerhalb derselben App)
        try:
            from timeline_window import TimelineWindow  # aus MakroTimelineViewer
            if not hasattr(self, "_timeline_windows"):
                self._timeline_windows = []
            # Viele Viewer erwarten beide Pfade; falls einer fehlt, einfach '' übergeben.
            win = TimelineWindow(str(actions_path) if actions_path.exists() else "",
                                 str(mouse_path)   if mouse_path.exists()   else "")
            win.show()
            self._timeline_windows.append(win)  # Referenz halten
            return
        except Exception as e:
            # Fallback: als separaten Prozess starten
            viewer_script = viewer_dir / "timeline_window.py"
            if viewer_script.exists():
                try:
                    subprocess.Popen([sys.executable, str(viewer_script),
                                      str(actions_path), str(mouse_path)])
                    return
                except Exception as e2:
                    self.statusBar().showMessage(f"Viewer-Start fehlgeschlagen: {e2}", 4000)
                    return
            self.statusBar().showMessage(f"TimelineViewer nicht gefunden: {e}", 4000)

    # ---------- Styles ----------
    def _apply_styles(self):
        self.setStyleSheet("""
        QMainWindow { background:#0a0a0a; color:#f2f2f2; }

        #fieldLabel {
            color:#9ea0a4; font-size:11px; letter-spacing:0.5px;
            margin-left:4px; margin-bottom:2px;
        }

        QLineEdit, QComboBox {
            background:#151515; color:#fff;
            border:1px solid #2b2b2b; border-radius:10px; padding:8px 12px;
        }
        QLineEdit:hover, QComboBox:hover { border-color:#3a3a3a; }
        QComboBox::drop-down { border:0; }
        QComboBox QAbstractItemView {
            background:#151515; color:#fff;
            selection-background-color:#ffbe44; selection-color:#111;
        }

        /* Clean, flacher Button */
        QPushButton {
            background:#FFB238; color:#111;
            border:none; border-radius:8px;
            padding:8px 14px; font-weight:600;
        }
        QPushButton:hover   { background:#ffc24d; }
        QPushButton:pressed { background:#e5a831; }

        /* Tabelle */
        QTableWidget {
            background:#0f0f0f; color:#eaeaea;
            alternate-background-color:#101010;
            border:1px solid #242424; border-radius:8px;
        }
        QHeaderView::section {
            background:#121212; color:#bfbfbf; border:0;
            padding:12px; font-weight:600;
            border-bottom:2px solid #FFB238;
        }

        /* Zeilen-Hover: sanft, aber klar sichtbar */
        QTableWidget::item:hover {
            background: rgba(255, 187, 80, 0.16);
        }

        /* Ausgewählte Zeile (bei Klick) */
        QTableWidget::item:selected {
            background: rgba(255, 187, 80, 0.26);
            color:#fff;
        }
        """)
