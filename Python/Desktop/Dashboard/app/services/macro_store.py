# app/services/macro_store.py
from __future__ import annotations
import os, json, shutil, uuid, datetime
from typing import List, Dict, Optional

APP_VENDOR = "EON"
APP_NAME = "MacroHub"


def _user_data_dir() -> str:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = os.path.join(appdata, APP_VENDOR, APP_NAME)
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share", APP_VENDOR, APP_NAME)
    os.makedirs(base, exist_ok=True)
    return base


class MacroStore:
    """
    Persistiert Makros im Benutzer-Datenordner:
      <appdata>/EON/MacroHub/macros/<id>/
        - meta.json
        - <original_name>.log
    Schnellzugriff: macros/index.json
    """
    def __init__(self) -> None:
        self.root = os.path.join(_user_data_dir(), "macros")
        os.makedirs(self.root, exist_ok=True)
        self.index_path = os.path.join(self.root, "index.json")
        if not os.path.exists(self.index_path):
            self._write_index([])

    # ---------------- public ----------------

    def load_all(self) -> List[Dict]:
        """Liest Index und säubert ihn gleichzeitig von fehlenden Makros."""
        idx = self._read_index()
        cleaned = self._clean_missing(idx)
        if cleaned != idx:
            self._write_index(cleaned)
        return cleaned

    def add_from_file(self, file_path: str) -> Dict:
        """Nimmt eine einzelne Datei als Makro. Name = Dateiname ohne Endung."""
        if not file_path or not os.path.isfile(file_path):
            raise FileNotFoundError("Datei nicht gefunden.")

        base = os.path.basename(file_path)
        name, _ = os.path.splitext(base)

        macro_id = str(uuid.uuid4())
        dst_dir = os.path.join(self.root, macro_id)
        os.makedirs(dst_dir, exist_ok=True)

        dst_file = os.path.join(dst_dir, base)
        shutil.copy2(file_path, dst_file)

        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        meta = {
            "id": macro_id,
            "name": name or "Unbenanntes Makro",
            "author": "Unbekannt",
            "category": "Utilities",
            "created_at": now_iso,
            "downloaded_at": now_iso,   # wird für Filter genutzt
            "hotkey": None,
            "version": 1,
            "file": base,
            "counts": {
                "lines": self._count_lines(dst_file)
            }
        }

        with open(os.path.join(dst_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        idx = self._read_index()
        idx.insert(0, meta)
        self._write_index(idx)
        return meta

    def dir_for(self, macro_id: str) -> str:
        return os.path.join(self.root, macro_id)

    # ---------------- private ----------------

    def _read_index(self) -> List[Dict]:
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_index(self, items: List[Dict]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def _count_lines(self, p: Optional[str]) -> int:
        if not p:
            return 0
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _clean_missing(self, idx: List[Dict]) -> List[Dict]:
        """Entfernt Index-Einträge, die im Dateisystem nicht mehr vorhanden sind."""
        cleaned: List[Dict] = []
        for m in idx:
            folder = os.path.join(self.root, m.get("id", ""))
            file_ok = False
            if os.path.isdir(folder):
                file_name = m.get("file")
                file_ok = bool(file_name and os.path.isfile(os.path.join(folder, file_name)))
            if file_ok:
                cleaned.append(m)
        return cleaned
