from __future__ import annotations

import os
import json
import shutil
import uuid
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------- AppData <-> Linux Pfad ----------
APP_VENDOR = "EON"
APP_NAME = "MacroHub"

def _user_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata) / APP_VENDOR / APP_NAME
    else:
        base = Path.home() / ".local" / "share" / APP_VENDOR / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


@dataclass
class FileNames:
    ACTIONS: str = "actions.log"
    ACTIONS_FIXED: str = "actions.fixed.log"
    MOVES: str = "mouse_moves.log"
    META: str = "meta.json"
    INDEX: str = "index.json"
    SCREENSHOTS: str = "screenshots"
    RESULTS: str = "results"


class MacroStore:
    """
    Robuster Store:
    - Root: <AppData>/EON/MacroHub/macros
    - load_all(): merged Index + tatsächliche Ordner (meta.json dominiert)
    - update_meta_fields(): aktualisiert meta.json **und** Index
    """

    def __init__(self, root: Optional[str | Path] = None) -> None:
        if root is None:
            root = _user_data_dir() / "macros"
        self.root: Path = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

        self._files = FileNames()
        self._index_path = self.root / self._files.INDEX
        if not self._index_path.exists():
            self._write_index([])

    # ---------- Index helpers ----------
    def _read_index(self) -> List[Dict[str, Any]]:
        try:
            if not self._index_path.exists():
                return []
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write_index(self, rows: List[Dict[str, Any]]) -> None:
        try:
            self._index_path.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _find_index_row(self, macro_id: str) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        rows = self._read_index()
        for i, r in enumerate(rows):
            if r.get("id") == macro_id:
                return i, r
        return None, None

    # ---------- Dir helpers ----------
    def dir_for(self, macro_id: str) -> str:
        return str(self.root / macro_id)

    def _guess_dir_for(self, macro_id: str) -> Optional[Path]:
        p = self.root / macro_id
        if (p / self._files.META).exists():
            return p
        # Fallback: ggf. alte Struktur durchsuchen
        for d in self.root.iterdir():
            if not d.is_dir():
                continue
            meta_path = d / self._files.META
            try:
                if meta_path.exists():
                    j = json.loads(meta_path.read_text(encoding="utf-8"))
                    if j.get("id") == macro_id:
                        return d
            except Exception:
                pass
        return None

    # ---------- Load & merge ----------
    def _load_meta_from_dir(self, d: Path) -> Optional[Dict[str, Any]]:
        meta_path = d / self._files.META
        if not meta_path.exists():
            return None
        try:
            j = json.loads(meta_path.read_text(encoding="utf-8"))
            # Defaults absichern
            j.setdefault("author", "")
            j.setdefault("category", "Utilities")
            j.setdefault("description", "")
            j.setdefault("extra", {})
            j.setdefault("hotkey", None)
            return j
        except Exception:
            return None

    def load_all(self) -> List[Dict[str, Any]]:
        """
        Liefert Makros; meta.json vom Datenträger dominiert, Index ist nur Snapshot.
        Scannt zusätzlich Ordner, die (noch) nicht im Index sind.
        """
        index_rows = self._read_index()
        results: List[Dict[str, Any]] = []

        # 1) Index-Einträge + merge mit Disk
        for r in index_rows:
            mid = r.get("id")
            if not mid:
                continue
            d = self._guess_dir_for(mid)
            disk = self._load_meta_from_dir(d) if d else None
            merged = dict(r)
            if disk:
                merged.update(disk)  # Disk dominiert
            results.append(merged)

        # 2) Ordner, die nicht im Index sind
        seen = {r.get("id") for r in results}
        for d in self.root.iterdir():
            if not d.is_dir():
                continue
            disk = self._load_meta_from_dir(d)
            if not disk:
                continue
            if disk.get("id") not in seen:
                results.append(disk)

        # Neueste oben
        def _key(x):
            return x.get("downloaded_at") or x.get("created_at") or ""
        return sorted(results, key=_key, reverse=True)

    # ---------- Create / Import ----------
    def add_from_zip(self, zip_path: str) -> Dict[str, Any]:
        import tempfile, zipfile
        if not zip_path or not Path(zip_path).is_file():
            raise FileNotFoundError("ZIP nicht gefunden.")
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(td)
            return self.add_from_folder(td)

    def add_from_folder(self, src: str) -> Dict[str, Any]:
        src_p = Path(src)
        mid = str(uuid.uuid4())
        dst = self.root / mid
        dst.mkdir(parents=True, exist_ok=True)

        # Logs kopieren (case-insensitive)
        def _resolve_case(p: Path, name: str) -> Optional[Path]:
            want = name.lower()
            for f in p.iterdir():
                if f.name.lower() == want:
                    return f
            return None

        for log in (self._files.ACTIONS, self._files.MOVES):
            src_log = _resolve_case(src_p, log)
            if not src_log:
                raise FileNotFoundError(f"{log} wurde nicht gefunden.")
            shutil.copy2(src_log, dst / log)

        # Optional: fixed + Ordner
        if (src_p / self._files.ACTIONS_FIXED).exists():
            shutil.copy2(src_p / self._files.ACTIONS_FIXED, dst / self._files.ACTIONS_FIXED)
        for opt in (self._files.SCREENSHOTS, self._files.RESULTS):
            s = src_p / opt
            if s.is_dir():
                shutil.copytree(s, dst / opt, dirs_exist_ok=True)

        counts = {
            self._files.ACTIONS: self._safe_count_lines(dst / self._files.ACTIONS),
            self._files.MOVES: self._safe_count_lines(dst / self._files.MOVES),
        }

        meta = {
            "id": mid,
            "name": dst.name,  # wird danach i.d.R. via update_meta_fields überschrieben
            "author": "",
            "category": "Utilities",
            "created_at": _now_iso(),
            "downloaded_at": _now_iso(),
            "hotkey": None,
            "version": 2,
            "files": [fn for fn in (self._files.ACTIONS, self._files.MOVES) if (dst / fn).exists()],
            "counts": counts,
            "description": "",
            "extra": {},
        }
        (dst / self._files.META).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self._add_to_index(meta)
        return meta

    # ---------- Update helpers ----------
    def _safe_count_lines(self, p: Path) -> int:
        try:
            if not p.exists():
                return 0
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _add_to_index(self, meta: Dict[str, Any]) -> None:
        rows = self._read_index()
        entry = {
            "id": meta.get("id"),
            "name": meta.get("name"),
            "author": meta.get("author", ""),
            "category": meta.get("category", "Utilities"),
            "downloaded_at": meta.get("downloaded_at"),
            "hotkey": meta.get("hotkey"),
            "description": meta.get("description", ""),
        }
        rows = [entry] + [r for r in rows if r.get("id") != entry["id"]]
        self._write_index(rows)

    # ---------- PUBLIC: Meta/Hotkey ----------
    def update_meta_fields(self, macro_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aktualisiert meta.json **und** Index. Erlaubte Keys: name, author, category,
        description, hotkey, extra.
        """
        d = self._guess_dir_for(macro_id)
        if not d:
            raise FileNotFoundError("Makro-Ordner nicht gefunden.")
        meta_path = d / self._files.META
        if not meta_path.exists():
            raise FileNotFoundError("meta.json fehlt.")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({k: v for k, v in fields.items() if k in {"name", "author", "category", "description", "hotkey", "extra"}})
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        # Index anpassen (falls vorhanden)
        rows = self._read_index()
        for i, r in enumerate(rows):
            if r.get("id") == macro_id:
                rows[i] = {
                    **r,
                    "name": meta.get("name", r.get("name")),
                    "author": meta.get("author", r.get("author", "")),
                    "category": meta.get("category", r.get("category", "Utilities")),
                    "downloaded_at": meta.get("downloaded_at", r.get("downloaded_at")),
                    "hotkey": meta.get("hotkey", r.get("hotkey")),
                    "description": meta.get("description", r.get("description", "")),
                }
                break
        else:
            # nicht im Index? -> hinzufügen
            self._add_to_index(meta)
            return meta

        self._write_index(rows)
        return meta

    def set_hotkey(self, macro_id: str, hotkey: Optional[str]) -> Dict[str, Any]:
        return self.update_meta_fields(macro_id, {"hotkey": hotkey or None})
