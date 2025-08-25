from __future__ import annotations
import os, json, shutil, uuid, datetime, zipfile
from typing import List, Dict, Optional, Tuple

APP_VENDOR = "EON"
APP_NAME = "MacroHub"

REQUIRED_LOGS = ("actions.log", "mouse_moves.log")
OPTIONAL_DIRS = ("screenshots", "results")


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
    <appdata>/EON/MacroHub/macros/<id>/
      - meta.json
      - actions.log
      - mouse_moves.log
      - screenshots/ (optional)
      - results/     (optional)
    Index: macros/index.json
    """
    def __init__(self) -> None:
        self.root = os.path.join(_user_data_dir(), "macros")
        os.makedirs(self.root, exist_ok=True)
        self.index_path = os.path.join(self.root, "index.json")
        if not os.path.exists(self.index_path):
            self._write_index([])

    # ---------------- public ----------------

    def load_all(self) -> List[Dict]:
        idx = self._read_index()
        cleaned = self._clean_missing(idx)
        if cleaned != idx:
            self._write_index(cleaned)
        return cleaned

    def add_from_zip(self, zip_path: str) -> Dict:
        if not zip_path or not os.path.isfile(zip_path):
            raise FileNotFoundError("ZIP nicht gefunden.")
        macro_id, dst_dir = self._alloc_dir()
        extract_dir = os.path.join(dst_dir, "_extract")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        src_dir = self._locate_log_root(extract_dir)
        if not src_dir:
            shutil.rmtree(dst_dir, ignore_errors=True)
            raise FileNotFoundError("Im ZIP wurden keine passenden Logs gefunden (actions.log / mouse_moves.log).")
        self._copy_macro_payload(src_dir, dst_dir)
        shutil.rmtree(extract_dir, ignore_errors=True)
        name = os.path.splitext(os.path.basename(zip_path))[0]
        meta = self._write_meta(dst_dir, macro_id, name)
        self._add_to_index(meta)
        return meta

    def add_from_folder(self, folder_path: str) -> Dict:
        if not folder_path or not os.path.isdir(folder_path):
            raise FileNotFoundError("Ordner nicht gefunden.")
        macro_id, dst_dir = self._alloc_dir()
        src_dir = self._locate_log_root(folder_path)
        if not src_dir:
            shutil.rmtree(dst_dir, ignore_errors=True)
            raise FileNotFoundError("Im Ordner wurden keine passenden Logs gefunden (actions.log / mouse_moves.log).")
        self._copy_macro_payload(src_dir, dst_dir)
        name = os.path.basename(os.path.normpath(folder_path))
        meta = self._write_meta(dst_dir, macro_id, name)
        self._add_to_index(meta)
        return meta

    def dir_for(self, macro_id: str) -> str:
        return os.path.join(self.root, macro_id)

    # --- Hotkey management ---

    def set_hotkey(self, macro_id: str, hotkey: Optional[str]) -> Dict:
        """
        Setzt/entfernt den Hotkey im meta.json und im Index.
        hotkey-Format: GlobalHotKeys-Style, z.B. '<ctrl>+<alt>+p'
        """
        folder = self.dir_for(macro_id)
        meta_path = os.path.join(folder, "meta.json")
        if not os.path.isfile(meta_path):
            raise FileNotFoundError("Makro-Metadatei fehlt.")
        meta = self._read_json(meta_path)
        meta["hotkey"] = hotkey or None
        self._write_json(meta_path, meta)

        idx = self._read_index()
        for i, m in enumerate(idx):
            if m.get("id") == macro_id:
                idx[i] = {**m, "hotkey": hotkey or None}
                break
        self._write_index(idx)
        return meta

    # ---------------- private helpers ----------------

    def _alloc_dir(self) -> Tuple[str, str]:
        macro_id = str(uuid.uuid4())
        dst_dir = os.path.join(self.root, macro_id)
        os.makedirs(dst_dir, exist_ok=True)
        return macro_id, dst_dir

    def _locate_log_root(self, search_root: str) -> Optional[str]:
        want = set(REQUIRED_LOGS)
        for cur, dirs, files in os.walk(search_root):
            fl = {f.lower() for f in files}
            if all(x in fl for x in want):
                return cur
        return None

    def _copy_macro_payload(self, src_dir: str, dst_dir: str) -> None:
        def resolve_case(path_dir: str, fname: str) -> Optional[str]:
            lf = fname.lower()
            for f in os.listdir(path_dir):
                if f.lower() == lf:
                    return os.path.join(path_dir, f)
            return None

        for log in REQUIRED_LOGS:
            src = resolve_case(src_dir, log)
            if not src:
                raise FileNotFoundError(f"{log} wurde nicht gefunden.")
            shutil.copy2(src, os.path.join(dst_dir, log))

        for opt in OPTIONAL_DIRS:
            src_opt = os.path.join(src_dir, opt)
            if os.path.isdir(src_opt):
                shutil.copytree(src_opt, os.path.join(dst_dir, opt), dirs_exist_ok=True)

    def _write_meta(self, dst_dir: str, macro_id: str, name: str) -> Dict:
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        counts = {}
        for log in REQUIRED_LOGS:
            p = os.path.join(dst_dir, log)
            counts[log] = self._count_lines(p) if os.path.isfile(p) else 0
        meta = {
            "id": macro_id,
            "name": name or "Unbenanntes Makro",
            "author": "Unbekannt",
            "category": "Utilities",
            "created_at": now_iso,
            "downloaded_at": now_iso,
            "hotkey": None,
            "version": 2,
            "files": list(REQUIRED_LOGS),
            "counts": counts
        }
        self._write_json(os.path.join(dst_dir, "meta.json"), meta)
        return meta

    def _add_to_index(self, meta: Dict) -> None:
        idx = self._read_index()
        idx.insert(0, meta)
        self._write_index(idx)

    def _read_index(self) -> List[Dict]:
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_index(self, items: List[Dict]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def _write_json(self, p: str, obj: Dict) -> None:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    def _read_json(self, p: str) -> Dict:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def _count_lines(self, p: Optional[str]) -> int:
        if not p:
            return 0
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _clean_missing(self, idx: List[Dict]) -> List[Dict]:
        cleaned: List[Dict] = []
        for m in idx:
            folder = os.path.join(self.root, m.get("id", ""))
            ok = os.path.isdir(folder)
            if ok:
                files = m.get("files") or []
                if files:
                    ok = all(os.path.isfile(os.path.join(folder, fn)) for fn in files)
                else:
                    ok = False
            if ok:
                cleaned.append(m)
        return cleaned
