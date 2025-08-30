from __future__ import annotations
import os
import sys
import json
import shutil
import signal
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from .macro_store import MacroStore


class RecorderError(Exception):
    pass


class RecorderService:
    """
    2-phase recorder:
      start_recording()  -> begin capture into temp folder
      end_recording()    -> stop capture, keep temp (user decides)
      save_recording()   -> import temp into MacroStore and cleanup
      discard_recording()-> delete temp and cleanup
    """

    def __init__(
        self,
        store: MacroStore,
        desktop_root: Optional[Path] = None,
        client_dir: Optional[Path] = None,
    ) -> None:
        self.store = store
        self._proc: Optional[subprocess.Popen] = None
        self._record_dir: Optional[Path] = None
        self.on_started: Optional[Callable[[Path], None]] = None
        self.on_stopped: Optional[Callable[[Optional[dict], Optional[str]], None]] = None

        if client_dir is not None:
            self.recorder_client_dir = Path(client_dir)
        else:
            env_dir = os.environ.get("EON_RECORDER_CLIENT")
            if env_dir:
                self.recorder_client_dir = Path(env_dir)
            else:
                fixed = Path(r"D:\DiplEON\EON\Python\Recorder-Client")
                if fixed.exists():
                    self.recorder_client_dir = fixed
                else:
                    if desktop_root is None:
                        desktop_root = Path(__file__).resolve().parents[3]  # .../Desktop
                    self.recorder_client_dir = desktop_root / "Recorder-Client"

    # ---- process state ----
    def is_recording(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ---- lifecycle ----
    def start_recording(self) -> Path:
        self._check_client_dir()
        if self.is_recording():
            raise RecorderError("A recording is already running.")

        record_dir = Path(tempfile.mkdtemp(prefix="macro_recording_"))
        (record_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        (record_dir / "results").mkdir(parents=True, exist_ok=True)
        self._record_dir = record_dir

        inline = (
            "import sys, os; "
            f"os.chdir(r'{record_dir.as_posix()}'); "
            f"sys.path.insert(0, r'{self.recorder_client_dir.as_posix()}'); "
            "from recorder_client import RecorderClient; "
            "RecorderClient().run()"
        )
        try:
            creation = (subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform.startswith("win") else 0)
            self._proc = subprocess.Popen(
                [sys.executable, "-c", inline],
                cwd=str(self.recorder_client_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation,
                text=True
            )
        except Exception as e:
            self._proc = None
            shutil.rmtree(record_dir, ignore_errors=True)
            raise RecorderError(f"Failed to start recorder: {e}") from e

        if self.on_started:
            try:
                self.on_started(record_dir)
            except Exception:
                pass

        return record_dir

    def end_recording(self) -> Path:
        if not self._record_dir:
            raise RecorderError("No active recording.")
        self._safe_terminate()
        return self._record_dir

    def save_recording(
        self,
        *,
        name: str,
        category: Optional[str] = None,   # momentan optional
        author: Optional[str] = None,
        hotkey: Optional[str] = None,
        description: Optional[str] = None,
        extra_meta: Optional[Dict[str, Any]] = None
    ) -> Optional[dict]:
        if not self._record_dir:
            raise RecorderError("No recording to save.")
        actions = self._record_dir / "actions.log"
        moves = self._record_dir / "mouse_moves.log"
        if not (actions.exists() and moves.exists()):
            tmp = self._record_dir
            self._record_dir = None
            shutil.rmtree(tmp, ignore_errors=True)
            raise RecorderError("Recording incomplete (missing actions.log or mouse_moves.log).")

        meta: Optional[dict] = None
        err: Optional[str] = None
        try:
            # 1) Importiert Ordner in den Store
            meta = self.store.add_from_folder(str(self._record_dir))
            macro_id = meta.get("id") if meta else None

            # 2) Felder vorbereiten (auch Description!)
            fields: Dict[str, Any] = {}
            if name:
                fields["name"] = name
            if author is not None:
                fields["author"] = author
            if category:
                fields["category"] = category
            if hotkey is not None:
                fields["hotkey"] = hotkey

            # description kommt entweder separat oder via extra_meta["description"]
            desc = description
            if desc is None and extra_meta and isinstance(extra_meta, dict):
                d2 = extra_meta.get("description")
                if isinstance(d2, str):
                    desc = d2
            if desc is not None:
                fields["description"] = desc

            if extra_meta:
                fields["extra"] = extra_meta

            # 3) Index + meta.json konsistent aktualisieren
            if macro_id:
                try:
                    meta = self.store.update_meta_fields(macro_id, fields)
                except Exception:
                    # Fallback: direkt in meta.json patchen
                    try:
                        macro_dir = Path(self.store.dir_for(macro_id))
                        meta_path = macro_dir / "meta.json"
                        j = json.loads(meta_path.read_text(encoding="utf-8"))
                        j.update({k: v for k, v in fields.items() if k != "extra"})
                        if "extra" in fields and isinstance(fields["extra"], dict):
                            j.setdefault("extra", {}).update(fields["extra"])
                        meta_path.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
                        meta = j
                    except Exception:
                        pass

        except Exception as e:
            err = str(e)
        finally:
            tmp = self._record_dir
            self._record_dir = None
            try:
                shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass
            if self.on_stopped:
                try:
                    self.on_stopped(meta, err)
                except Exception:
                    pass

        if err:
            raise RecorderError(f"Save failed: {err}")
        return meta

    def discard_recording(self) -> None:
        if self.is_recording():
            self._safe_terminate()
        if self._record_dir:
            try:
                shutil.rmtree(self._record_dir, ignore_errors=True)
            except Exception:
                pass
        self._record_dir = None

    # ---- helpers ----
    def _safe_terminate(self):
        if not self._proc:
            return
        try:
            if sys.platform.startswith("win"):
                try:
                    self._proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                except Exception:
                    self._proc.terminate()
            else:
                self._proc.terminate()
            self._proc.wait(timeout=2)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        finally:
            self._proc = None

    def _check_client_dir(self) -> None:
        if not self.recorder_client_dir.exists():
            raise RecorderError(
                "Recorder-Client not found: "
                f"{self.recorder_client_dir}\n"
                "Tip: pass client_dir=Path(r'D:\\DiplEON\\EON\\Python\\Recorder-Client') "
                "or set EON_RECORDER_CLIENT env var."
            )
        if not (self.recorder_client_dir / "recorder_client.py").exists():
            raise RecorderError(
                f"Recorder-Client incomplete (recorder_client.py missing) in {self.recorder_client_dir}"
            )
