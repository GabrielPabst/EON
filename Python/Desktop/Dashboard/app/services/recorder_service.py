from __future__ import annotations
import os
import sys
import shutil
import signal
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Callable

from .macro_store import MacroStore


class RecorderError(Exception):
    pass


class RecorderService:
    """
    Startet/stoppt die Aufnahme über den externen 'Recorder-Client' als Subprozess.
    - zeichnet in einen temporären Ordner auf
    - beim Stop wird der Ordner in den MacroStore importiert (add_from_folder)
    - liefert das neue Meta (Makro) zurück

    Callbacks:
      - on_started(record_dir: Path)
      - on_stopped(meta: Optional[dict], error: Optional[str])
    """

    def __init__(self, store: MacroStore, desktop_root: Optional[Path] = None) -> None:
        self.store = store
        self._proc: Optional[subprocess.Popen] = None
        self._tmp_dir: Optional[Path] = None
        self.on_started: Optional[Callable[[Path], None]] = None
        self.on_stopped: Optional[Callable[[Optional[dict], Optional[str]], None]] = None

        if desktop_root is None:
            desktop_root = Path(__file__).resolve().parents[3]
        self.desktop_root = desktop_root
        self.recorder_client_dir = self.desktop_root / "Recorder-Client"

    def _check_client_dir(self) -> None:
        if not self.recorder_client_dir.exists():
            raise RecorderError(f"Recorder-Client nicht gefunden: {self.recorder_client_dir}")
        if not (self.recorder_client_dir / "recorder_client.py").exists():
            raise RecorderError("Recorder-Client ist unvollständig (recorder_client.py fehlt).")

    def is_recording(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start_recording(self, suggested_name: Optional[str] = None) -> Path:
        if self.is_recording():
            raise RecorderError("Es läuft bereits eine Aufnahme.")

        self._check_client_dir()

        # Temp-Ordner anlegen (zeichnet dort actions.log / mouse_moves.log / screenshots ab)
        tmp_dir = Path(tempfile.mkdtemp(prefix="macro_recording_"))
        self._tmp_dir = tmp_dir

        # Start Recorder als Subprozess (im CWD=tmp_dir)
        # recorder_client.py beendet sich von selbst, wenn Nutzer 'q' drückt
        try:
            self._proc = subprocess.Popen(
                [sys.executable, "recorder_client.py"],
                cwd=str(self.recorder_client_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform.startswith("win") else 0,
                text=True,
                # WICHTIG: wir setzen die Arbeitsausgabe in unseren tmp_dir um,
                # indem wir die env "PYTHONPATH" so setzen, dass pyautogui/pynput
                # normal laufen – die Dateien schreibt recorder_client relativ
                # zu seinem *aktuellen Prozess*, also CWD=recorder_client_dir!
                # -> Daher ändern wir nicht PYTHONPATH, sondern geben dem Script
                #    per arg ein Ziel – ABER recorder_client.py unterstützt das
                #    derzeit nicht. Workaround: Start in Recorder-Client, aber
                #    mit chdir in den tmp_dir via Inline-Python.
            )
        except Exception as e:
            self._proc = None
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise RecorderError(f"Recorder-Start fehlgeschlagen: {e}") from e

        # ACHTUNG: recorder_client.py schreibt aktuell in sein CWD.
        # Deshalb starten wir einen Mini-Helfer, der im tmp_dir läuft und
        # recorder_client importiert *und* os.chdir(tmp_dir) setzt.
        # -> wir ersetzen den obigen Start durch Inline-Runner:
        try:
            # Kill den oben gestarteten Prozess sofort wieder (wir ersetzen ihn).
            self._safe_kill()
        except Exception:
            pass

        inline = (
            "import sys, os; "
            f"os.chdir(r'{tmp_dir.as_posix()}'); "
            f"sys.path.insert(0, r'{self.recorder_client_dir.as_posix()}'); "
            "from recorder_client import RecorderClient; "
            "RecorderClient().run()"
        )

        try:
            self._proc = subprocess.Popen(
                [sys.executable, "-c", inline],
                cwd=str(self.recorder_client_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform.startswith("win") else 0,
                text=True
            )
        except Exception as e:
            self._proc = None
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise RecorderError(f"Recorder-Start fehlgeschlagen: {e}") from e

        if self.on_started:
            try: self.on_started(tmp_dir)
            except Exception: pass

        return tmp_dir

    def stop_recording(self) -> Optional[dict]:
        """
        Stoppt die Aufnahme:
          - beendet den Subprozess
          - importiert den tmp-Ordner in den MacroStore (falls Logs vorhanden)
          - räumt tmp auf
        Gibt das neue Makro-Meta zurück (oder None bei Fehler).
        """
        if not self._tmp_dir:
            # nichts zu stoppen
            return None

        meta: Optional[dict] = None
        err: Optional[str] = None

        try:
            # Recorder sauber beenden
            self._safe_terminate()

            # Prüfen, ob die beiden Logs da sind
            actions = self._tmp_dir / "actions.log"
            moves = self._tmp_dir / "mouse_moves.log"
            if not (actions.exists() and moves.exists()):
                err = "Aufnahme unvollständig (actions.log / mouse_moves.log fehlen)."
            else:
                # In den Store importieren
                try:
                    meta = self.store.add_from_folder(str(self._tmp_dir))
                except Exception as e:
                    err = f"Import in MacroStore fehlgeschlagen: {e}"
        finally:
            # tmp aufräumen
            try:
                shutil.rmtree(self._tmp_dir, ignore_errors=True)
            except Exception:
                pass
            self._tmp_dir = None

            if self.on_stopped:
                try: self.on_stopped(meta, err)
                except Exception: pass

        if err:
            raise RecorderError(err)
        return meta

    # ---------------- intern ----------------

    def _safe_terminate(self):
        if not self._proc:
            return
        try:
            if sys.platform.startswith("win"):
                self._proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            else:
                self._proc.terminate()
            self._proc.wait(timeout=2)
        except Exception:
            try:
                if self._proc:
                    self._proc.kill()
            except Exception:
                pass
        finally:
            self._proc = None

    def _safe_kill(self):
        if not self._proc:
            return
        try:
            self._proc.kill()
        except Exception:
            pass
        finally:
            self._proc = None
