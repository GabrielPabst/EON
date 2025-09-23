from __future__ import annotations

import os
import json
import shutil
import uuid
import datetime
import zipfile
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


APP_VENDOR = "EON"
APP_NAME = "MacroHub"


def _canonical(p: str | Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.path.expandvars(str(p)))))


def _user_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = _canonical(Path(appdata) / APP_VENDOR / APP_NAME)
    else:
        base = _canonical(Path.home() / ".local" / "share" / APP_VENDOR / APP_NAME)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _settings_path() -> Path:
    """JSON mit { "macro_root": "<path>" }."""
    return _user_data_dir() / "settings.json"


def _load_settings() -> Dict[str, Any]:
    sp = _settings_path()
    try:
        if sp.exists():
            return json.loads(sp.read_text(encoding="utf-8")) or {}
    except Exception:
        pass
    return {}


def _save_settings(d: Dict[str, Any]) -> None:
    sp = _settings_path()
    try:
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


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
    # ----------------- Config (Root) -----------------
    @staticmethod
    def get_config_root() -> Path:
        st = _load_settings()
        p = st.get("macro_root")
        if p:
            return _canonical(p)
        return _canonical(_user_data_dir() / "macros")

    @staticmethod
    def save_config_root(p: str | Path) -> None:
        st = _load_settings()
        st["macro_root"] = str(_canonical(p))
        _save_settings(st)

    # ----------------- Lifecycle -----------------
    def __init__(self, root: Optional[str | Path] = None) -> None:
        if root is None:
            root = self.get_config_root()
        self.root: Path = _canonical(root)
        self.root.mkdir(parents=True, exist_ok=True)

        self._files = FileNames()
        self._index_path = self.root / self._files.INDEX
        if not self._index_path.exists():
            self._write_index([])

    # ----------------- Root switch / Migration -----------------
    def probe_macros(self, base: Optional[str | Path] = None) -> List[Path]:
        """
        Finde Macro-Ordner in 'base': Ordner, die eine meta.json enthalten.
        """
        base_p = _canonical(base or self.root)
        out: List[Path] = []
        try:
            for d in base_p.iterdir():
                if not d.is_dir():
                    continue
                if (d / self._files.META).exists():
                    out.append(d)
        except Exception:
            pass
        return out

    def set_root(self, new_root: str | Path, migrate: Optional[str] = "copy") -> None:
        """
        Root-Verzeichnis wechseln und optional vorhandene Macros migrieren.
        migrate: "copy" | "move" | None
        """
        new_root_p = _canonical(new_root)
        old_root_p = self.root

        if new_root_p == old_root_p:
            # nichts zu tun
            self.save_config_root(new_root_p)
            return

        new_root_p.mkdir(parents=True, exist_ok=True)

        if migrate in ("copy", "move"):
            # Macro-Ordner rüberbringen
            for d in self.probe_macros(old_root_p):
                dest = new_root_p / d.name
                try:
                    if dest.exists():
                        # Kollisionsschutz: vorhandenes Ziel nicht überschreiben
                        continue
                    if migrate == "copy":
                        shutil.copytree(d, dest, dirs_exist_ok=False)
                    else:
                        shutil.move(str(d), str(dest))
                except Exception:
                    # bei Fehler: einfach nächsten versuchen
                    continue

            # index.json mitnehmen (falls vorhanden)
            try:
                old_index = old_root_p / self._files.INDEX
                if old_index.exists():
                    dest_index = new_root_p / self._files.INDEX
                    if migrate == "copy":
                        shutil.copy2(old_index, dest_index)
                    else:
                        # move: wenn Ziel schon existiert, nicht überschreiben
                        if not dest_index.exists():
                            shutil.move(str(old_index), str(dest_index))
            except Exception:
                pass

        # Root umstellen
        self.root = new_root_p
        self._index_path = self.root / self._files.INDEX
        if not self._index_path.exists():
            self._write_index([])

        # Setting persistieren
        self.save_config_root(self.root)

    # ----------------- Index helpers -----------------
    def _read_index(self) -> List[Dict[str, Any]]:
        try:
            if not self._index_path.exists():
                return []
            txt = self._index_path.read_text(encoding="utf-8")
            return json.loads(txt) if txt.strip() else []
        except Exception:
            return []

    def _write_index(self, rows: List[Dict[str, Any]]) -> None:
        try:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
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

    # ----------------- Path helpers -----------------
    def dir_for(self, macro_id: str) -> str:
        return str(_canonical(self.root / macro_id))

    def _guess_dir_for(self, macro_id: str) -> Optional[Path]:
        p = _canonical(self.root / macro_id)
        if (p / self._files.META).exists():
            return p
        try:
            for d in self.root.iterdir():
                if not d.is_dir():
                    continue
                meta_path = d / self._files.META
                if not meta_path.exists():
                    continue
                try:
                    j = json.loads(meta_path.read_text(encoding="utf-8"))
                    if j.get("id") == macro_id:
                        return d
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def find_existing_dir(self, macro_id: str) -> Optional[str]:
        d = self._guess_dir_for(macro_id)
        return str(d) if d else None

    # ----------------- Meta helpers -----------------
    def _load_meta_from_dir(self, d: Path) -> Optional[Dict[str, Any]]:
        meta_path = d / self._files.META
        if not meta_path.exists():
            return None
        try:
            j = json.loads(meta_path.read_text(encoding="utf-8"))
            # Vorrang: Name aus JSON, sonst Ordnername
            j.setdefault("id", d.name)
            j.setdefault("name", d.name)
            j.setdefault("author", "")
            j.setdefault("category", "Utilities")
            j.setdefault("description", "")
            j.setdefault("extra", {})
            j.setdefault("hotkey", None)

            files = j.get("files")
            if not files or not isinstance(files, list):
                files = []
                for fn in (self._files.ACTIONS, self._files.MOVES, self._files.ACTIONS_FIXED):
                    if (d / fn).exists():
                        files.append(fn)
                j["files"] = files

            counts = j.get("counts")
            if not counts or not isinstance(counts, dict):
                counts = {
                    self._files.ACTIONS: self._safe_count_lines(d / self._files.ACTIONS),
                    self._files.MOVES: self._safe_count_lines(d / self._files.MOVES),
                }
                j["counts"] = counts

            return j
        except Exception:
            return None

    def get_display_name(self, macro_id: str) -> str:
        """Bevorzugt name aus meta.json, fallback: Ordnername, fallback: macro_id."""
        d = self._guess_dir_for(macro_id)
        if d and (d / self._files.META).exists():
            try:
                j = json.loads((d / self._files.META).read_text(encoding="utf-8"))
                nm = (j.get("name") or "").strip()
                if nm:
                    return nm
            except Exception:
                pass
            return d.name
        return macro_id

    # ----------------- Load / add / update -----------------
    def load_all(self) -> List[Dict[str, Any]]:
        index_rows = self._read_index()
        results: List[Dict[str, Any]] = []
        valid_ids: List[str] = []

        for r in index_rows:
            mid = r.get("id")
            if not mid:
                continue
            d = self._guess_dir_for(mid)
            if not d:
                continue
            disk = self._load_meta_from_dir(d)
            if not disk:
                continue

            merged = dict(r)
            merged.update(disk)
            merged.setdefault("name", merged.get("id", "Unnamed"))
            merged.setdefault("description", "")
            merged.setdefault("author", "")
            merged.setdefault("category", "Utilities")
            merged.setdefault("hotkey", None)

            results.append(merged)
            valid_ids.append(mid)

        seen = set(valid_ids)
        try:
            for d in self.root.iterdir():
                if not d.is_dir():
                    continue
                disk = self._load_meta_from_dir(d)
                if not disk:
                    continue
                if disk.get("id") not in seen:
                    results.append(disk)
                    valid_ids.append(disk.get("id"))
        except Exception:
            pass

        old_ids = [r.get("id") for r in index_rows if r.get("id")]
        if set(old_ids) != set(valid_ids):
            try:
                rows_out: List[Dict[str, Any]] = []
                for meta in results:
                    rows_out.append({
                        "id": meta.get("id"),
                        "name": meta.get("name"),
                        "author": meta.get("author", ""),
                        "category": meta.get("category", "Utilities"),
                        "downloaded_at": meta.get("downloaded_at"),
                        "hotkey": meta.get("hotkey"),
                        "description": meta.get("description", ""),
                    })
                def _key(x):
                    return x.get("downloaded_at") or x.get("created_at") or ""
                rows_out = sorted(rows_out, key=_key, reverse=True)
                self._write_index(rows_out)
            except Exception:
                pass

        def _key_res(x):
            return x.get("downloaded_at") or x.get("created_at") or ""
        return sorted(results, key=_key_res, reverse=True)

    def add_from_zip(self, zip_path: str) -> Dict[str, Any]:
        import tempfile
        p = Path(zip_path)
        if not zip_path or not p.is_file():
            raise FileNotFoundError("ZIP nicht gefunden.")
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            with zipfile.ZipFile(p, "r") as zf:
                zf.extractall(td)

            # Falls das ZIP genau einen Top-Level-Ordner enthält, in diesen Ordner wechseln
            entries = [e for e in td_p.iterdir() if not e.name.startswith("__MACOSX")]
            if len(entries) == 1 and entries[0].is_dir():
                src_root = entries[0]
            else:
                # sonst: direkt das temp-Verzeichnis nutzen
                src_root = td_p

            return self.add_from_folder(str(src_root))

    def _try_load_src_meta(self, src_p: Path) -> Optional[Dict[str, Any]]:
        """Liest (falls vorhanden) eine meta.json im Quellordner und gibt sie zurück."""
        meta_path = src_p / self._files.META
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _find_macro_payload_root(self, src_p: Path) -> Path:
        """
        Falls der Nutzer einen Top-Level-Ordner wählt, in dem der eigentliche Macro-Inhalt
        erst in einem Unterordner liegt, finde automatisch den richtigen Ordner.
        Regeln:
          - Wenn src_p bereits actions.log / mouse_moves.log (case-insensitive) enthält -> src_p
          - Wenn es genau EINEN Unterordner gibt -> nimm diesen (sofern er Logs hat; sonst später rekursiv)
          - Sonst: suche rekursiv nach einem Ordner, der actions.log (oder actions.fixed.log) enthält
        """
        def _has_logs(p: Path) -> bool:
            try:
                names = {f.name.lower() for f in p.iterdir() if f.is_file()}
            except Exception:
                return False
            has_actions = ("actions.log" in names) or ("actions.fixed.log" in names)
            # mouse_moves.log ist nice-to-have, aber nicht zwingend
            return has_actions

        # 1) Direkt im gewählten Ordner?
        if src_p.is_dir() and _has_logs(src_p):
            return src_p

        # 2) Genau ein Unterordner?
        try:
            subdirs = [d for d in src_p.iterdir() if d.is_dir() and not d.name.startswith("__MACOSX")]
        except Exception:
            subdirs = []
        if len(subdirs) == 1:
            inner = subdirs[0]
            if _has_logs(inner):
                return inner

        # 3) Rekursiv suchen
        try:
            for d in src_p.rglob("*"):
                if d.is_dir() and _has_logs(d):
                    return d
        except Exception:
            pass

        # Fallback: original (führt ggf. zu "actions.log wurde nicht gefunden.")
        return src_p

    def add_from_folder(self, src: str) -> Dict[str, Any]:
        src_p = _canonical(src)
        # ➜ Payload-Root finden (springt in den einzigen Unterordner oder sucht die Logs)
        src_p = self._find_macro_payload_root(src_p)

        mid = str(uuid.uuid4())
        dst = _canonical(self.root / mid)
        dst.mkdir(parents=True, exist_ok=True)

        def _resolve_case(p: Path, name: str) -> Optional[Path]:
            want = name.lower()
            try:
                for f in p.iterdir():
                    if f.name.lower() == want:
                        return f
            except Exception:
                pass
            return None

        for log in (self._files.ACTIONS, self._files.MOVES):
            src_log = _resolve_case(src_p, log)
            if not src_log:
                raise FileNotFoundError(f"{log} wurde nicht gefunden.")
            shutil.copy2(src_log, dst / log)

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

        # Name priorisieren: meta.json im Source > Ordnername
        src_meta = self._try_load_src_meta(src_p) or {}
        src_name = (src_meta.get("name") or "").strip()
        default_name = src_name or (src_p.name or dst.name)

        meta = {
            "id": mid,
            "name": default_name,
            "author": src_meta.get("author", ""),
            "category": src_meta.get("category", "Utilities"),
            "created_at": src_meta.get("created_at", _now_iso()),
            "downloaded_at": _now_iso(),
            "hotkey": None,
            "version": 2,
            "files": [fn for fn in (self._files.ACTIONS, self._files.MOVES) if (dst / fn).exists()],
            "counts": counts,
            "description": src_meta.get("description", ""),
            "extra": src_meta.get("extra", {}),
        }
        (dst / self._files.META).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self._add_to_index(meta)
        return meta

    # ----------------- Utils -----------------
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

    def update_meta_fields(self, macro_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        d = self._guess_dir_for(macro_id)
        if not d:
            raise FileNotFoundError("Makro-Ordner nicht gefunden.")
        meta_path = d / self._files.META
        if not meta_path.exists():
            raise FileNotFoundError("meta.json fehlt.")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        update: Dict[str, Any] = {}
        for k in ("name", "author", "category", "description", "hotkey"):
            if k in fields:
                update[k] = fields[k]

        if "extra" in fields and isinstance(fields["extra"], dict):
            base_extra = meta.get("extra", {})
            if not isinstance(base_extra, dict):
                base_extra = {}
            merged_extra = dict(base_extra)
            merged_extra.update(fields["extra"])
            update["extra"] = merged_extra
        elif "extra" in fields:
            update["extra"] = fields["extra"]

        meta.update(update)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

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
                self._write_index(rows)
                break
        else:
            self._add_to_index(meta)

        return meta

    def set_hotkey(self, macro_id: str, hotkey: Optional[str]) -> Dict[str, Any]:
        return self.update_meta_fields(macro_id, {"hotkey": hotkey or None})

    def delete_macro(self, macro_id: str) -> bool:
        removed = False
        try:
            d = self._guess_dir_for(macro_id)
            if d and d.exists():
                shutil.rmtree(d, ignore_errors=True)
                removed = True
        except Exception:
            pass
        try:
            rows = self._read_index()
            new_rows = [r for r in rows if r.get("id") != macro_id]
            if len(new_rows) != len(rows):
                self._write_index(new_rows)
                removed = True
        except Exception:
            pass
        return removed

    # ----------------- Export helpers -----------------
    @staticmethod
    def sanitize_export_basename(name: str, compact: bool = True) -> str:
        """
        Macht einen sauberen Dateinamen daraus.
        - Entfernt verbotene Zeichen \/:*?"<>|
        - Entfernt führende/trailing Punkte/Spaces
        - compact=True: entfernt alle Whitespaces komplett (z.B. 'Schreibe Filip' -> 'SchreibeFilip')
          compact=False: ersetzt Whitespaces durch '_'
        - Reduziert auf erlaubte Zeichen [A-Za-z0-9._-] nach Cleanup
        """
        if not name:
            return "macro"
        # Entferne verbotene Zeichen
        cleaned = re.sub(r'[\\/:*?"<>|]', "", name)
        cleaned = cleaned.strip(" .")

        if compact:
            cleaned = re.sub(r"\s+", "", cleaned)   # Whitespaces entfernen
        else:
            cleaned = re.sub(r"\s+", "_", cleaned)  # Whitespaces -> "_"

        cleaned = re.sub(r"[^A-Za-z0-9._-]", "", cleaned)
        return cleaned or "macro"

    def suggest_export_basename(self, macro_id: str) -> str:
        display_name = self.get_display_name(macro_id)
        return self.sanitize_export_basename(display_name, compact=True)

    # ----------------- Export as ZIP -----------------
    def export_zip(self, macro_id: str, out_path: str | Path) -> str:
        """
        Packt den gesamten Makro-Ordner als ZIP nach `out_path`.
        Nicht-destruktiv (Makro bleibt erhalten).
        Gibt den finalen Pfad als String zurück.
        """
        d = self._guess_dir_for(macro_id)
        if not d or not d.exists():
            raise FileNotFoundError("Makro-Ordner nicht gefunden.")

        out = _canonical(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() != ".zip":
            out = out.with_suffix(".zip")

        root_name = d.name
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in d.rglob("*"):
                if file.is_file():
                    rel = file.relative_to(d)
                    arc = Path(root_name) / rel
                    zf.write(file, arcname=str(arc).replace("\\", "/"))

        return str(out)
