# app/services/replay_service.py
from __future__ import annotations

import json
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any, Tuple

from .macro_store import MacroStore


class ReplayError(Exception):
    pass


_SCREENSHOT_RE = re.compile(r"screenshot_(\d+)_([-\d]+)_([-\d]+)\.png$", re.IGNORECASE)


def _parse_name(fname: str) -> Optional[Tuple[int, int, int]]:
    """
    Extrahiert (ts, x, y) aus 'screenshot_<ts>_<x>_<y>.png'.
    Gibt None zurück, wenn das Schema nicht passt.
    """
    m = _SCREENSHOT_RE.search(fname)
    if not m:
        return None
    ts = int(m.group(1))
    x = int(m.group(2))
    y = int(m.group(3))
    return ts, x, y


class ReplayService:
    """
    Dünner Wrapper um den externen Makro-Client:
    - nutzt MacroReplayManager (aus macro_replay.py) unverändert
    - ruft replay_all() auf
    - setzt cwd = Makro-Ordner (für relative 'screenshots/' & 'results/')
    - legt 'screenshots'/'results' vorsorglich an
    - NORMALISIERT die 'screenshot'-Pfade in actions.log -> actions.fixed.log
      (sucht bestes vorhandenes Icon im screenshots-Ordner)
    """

    def __init__(self, store: MacroStore, client_dir: Optional[Path] = None) -> None:
        self.store = store
        self._proc: Optional[subprocess.Popen] = None
        self._running_id: Optional[str] = None
        self.on_started: Optional[Callable[[str], None]] = None
        self.on_finished: Optional[Callable[[str, Optional[str]], None]] = None

        self.client_dir: Path = client_dir or self._find_client_dir()
        if not (self.client_dir / "macro_replay.py").exists():
            raise ReplayError(
                f"Makro-Client unvollständig: {self.client_dir}\\macro_replay.py fehlt"
            )

    # ---------------- public API ----------------

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start_replay(self, macro_id: str) -> None:
        if self.is_running():
            raise ReplayError("Es läuft bereits ein Replay. Bitte zuerst stoppen.")

        macro_dir = Path(self.store.dir_for(macro_id))
        actions = macro_dir / "actions.log"
        moves = macro_dir / "mouse_moves.log"
        if not actions.exists() or not moves.exists():
            raise ReplayError(f"Benötigt: {actions.name} + {moves.name} in {macro_dir}")

        # Vorsorglich: Ordner anlegen, falls der Client dort schreibt
        (macro_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        (macro_dir / "results").mkdir(parents=True, exist_ok=True)

        # Actions-Datei vorbereiten (alle Icon-Pfade auf existierende Dateien mappen)
        fixed_actions = self._prepare_actions_file(macro_dir, actions)

        # Minimaler Inline-Code: importiere SEIN macro_replay und starte replay_all()
        inline = (
            "import sys\n"
            f"sys.path.insert(0, r'{self.client_dir.as_posix()}')\n"
            "from macro_replay import MacroReplayManager\n"
            f"m = MacroReplayManager(mouse_log=r'{moves.as_posix()}', actions_log=r'{fixed_actions.as_posix()}')\n"
            "m.replay_all()\n"
        )

        creation_flags = 0
        if sys.platform.startswith("win"):
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

        try:
            # cwd = Makro-Ordner -> relative 'screenshots/...'-Pfade stimmen
            self._proc = subprocess.Popen(
                [sys.executable, "-c", inline],
                cwd=str(macro_dir),
                creationflags=creation_flags,
            )
            self._running_id = macro_id
            if self.on_started:
                try:
                    self.on_started(macro_id)
                except Exception:
                    pass
        except Exception as e:
            self._proc = None
            self._running_id = None
            raise ReplayError(f"Replay-Start fehlgeschlagen: {e}") from e

    def poll_finish(self) -> Optional[str]:
        if not self._proc:
            return None
        code = self._proc.poll()
        if code is None:
            return None

        err: Optional[str] = None
        if code != 0:
            err = f"Replay-Prozess endete mit Code {code}."

        rid = self._running_id or ""
        self._proc = None
        self._running_id = None
        if self.on_finished:
            try:
                self.on_finished(rid, err)
            except Exception:
                pass
        return err

    def stop_replay(self) -> None:
        if not self.is_running():
            return

        proc = self._proc
        self._proc = None
        rid = self._running_id or ""
        self._running_id = None
        if proc is None:
            return

        try:
            if sys.platform.startswith("win"):
                try:
                    proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                    proc.wait(timeout=2)
                except Exception:
                    pass
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        capture_output=True,
                        text=True,
                    )
                except Exception:
                    pass
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except Exception:
                    proc.kill()
        finally:
            if self.on_finished:
                try:
                    self.on_finished(rid, None)
                except Exception:
                    pass

    # ---------------- helpers ----------------

    def _find_client_dir(self) -> Path:
        """
        Sucht 'Makro-Client' neben Desktop/Dashboard/Python.
        Wenn du einen fixen Pfad hast, gib ihn beim Konstruktor rein.
        """
        here = Path(__file__).resolve()
        desktop_dir = here.parents[3]       # .../Desktop
        dashboard_dir = here.parents[2]     # .../Desktop/Dashboard
        python_dir = desktop_dir.parent     # .../Python

        candidates = [
            desktop_dir / "Makro-Client",
            python_dir / "Makro-Client",            # dein üblicher Pfad
            dashboard_dir.parent / "Makro-Client",
        ]
        for c in candidates:
            if c.exists():
                return c

        tried = " | ".join(str(c) for c in candidates)
        raise ReplayError(f"Makro-Client nicht gefunden. Versuchte Pfade: {tried}")

    # -------- actions.log -> actions.fixed.log mit Pfad-Resolver --------

    def _prepare_actions_file(self, macro_dir: Path, actions_path: Path) -> Path:
        """
        Liest actions.log (JSON lines) und normalisiert 'screenshot'-Pfade:
        - Existiert der Pfad? -> wenn er im lokalen screenshots/-Ordner liegt, relativ schreiben.
        - Sonst im <macro_dir>/screenshots/ bestmögliches Icon suchen:
            1) exakter Name
            2) gleicher (x,y), nächstliegender ts
            3) beliebiger nächstliegender ts
            4) fallback: screenshot_.png (falls vorhanden)
        - Schreibt nach actions.fixed.log und gibt diesen Pfad zurück.
        """
        fixed_path = macro_dir / "actions.fixed.log"
        screenshots_dir = macro_dir / "screenshots"

        # Index der vorhandenen Screenshots bauen
        all_pngs = sorted(screenshots_dir.glob("*.png"))
        by_xy: Dict[Tuple[int, int], List[Tuple[int, Path]]] = {}
        by_ts: List[Tuple[int, Path]] = []
        fallback_blank = screenshots_dir / "screenshot_.png"

        for p in all_pngs:
            meta = _parse_name(p.name)
            if not meta:
                if p.name.lower() == "screenshot_.png":
                    continue  # fallback separat
                continue
            ts, x, y = meta
            by_ts.append((ts, p))
            by_xy.setdefault((x, y), []).append((ts, p))

        by_ts.sort()
        for lst in by_xy.values():
            lst.sort()

        def nearest_by_ts(target_ts: int, candidates: List[Tuple[int, Path]]) -> Optional[Path]:
            if not candidates:
                return None
            best = None
            best_d = 1 << 62
            for ts, p in candidates:
                d = abs(ts - target_ts)
                if d < best_d:
                    best_d = d
                    best = p
            return best

        def rel_in_screenshots(p: Path) -> str:
            # garantiert Forward Slashes + relativer Pfad
            return f"screenshots/{p.name}"

        def resolve_icon(requested_path: str) -> str:
            abs_req = Path(requested_path)

            # 0) Falls der exakte Pfad existiert:
            if abs_req.exists():
                # Wenn er im lokalen screenshots/-Ordner liegt -> relativ zurückgeben
                try:
                    abs_req.relative_to(screenshots_dir)
                    return rel_in_screenshots(abs_req)
                except Exception:
                    # Liegt außerhalb -> notfalls posix-abs Pfad beibehalten
                    return abs_req.as_posix()

            # 1) Gleichnamige Datei im lokalen screenshots/-Ordner?
            candidate = screenshots_dir / abs_req.name
            if candidate.exists():
                return rel_in_screenshots(candidate)

            # 2) Metadaten aus gewünschtem Namen ziehen und bestes Match im lokalen Ordner finden
            meta = _parse_name(abs_req.name)
            if meta:
                ts, x, y = meta
                # 2a) gleicher (x,y) -> nächstliegender ts
                lst = by_xy.get((x, y), [])
                p = nearest_by_ts(ts, lst)
                if p:
                    return rel_in_screenshots(p)
                # 2b) global nächstliegender ts
                p = nearest_by_ts(ts, by_ts)
                if p:
                    return rel_in_screenshots(p)

            # 3) Fallback: screenshot_.png
            if fallback_blank.exists():
                return rel_in_screenshots(fallback_blank)

            # 4) Letzte Rettung: irgendeine vorhandene Datei (im lokalen Ordner -> relativ)
            if all_pngs:
                return rel_in_screenshots(all_pngs[0])

            # 5) Gar nichts gefunden -> Originalpfad posix-normalisiert zurückgeben
            return abs_req.as_posix()

        lines_out: List[str] = []
        with actions_path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    evt: Dict[str, Any] = json.loads(raw)
                except Exception:
                    lines_out.append(raw + "\n")
                    continue

                if evt.get("type") in ("press", "release"):
                    shot = evt.get("screenshot", "")
                    if isinstance(shot, str) and shot:
                        evt["screenshot"] = resolve_icon(shot)

                lines_out.append(json.dumps(evt, ensure_ascii=False) + "\n")

        with fixed_path.open("w", encoding="utf-8") as w:
            w.writelines(lines_out)

        return fixed_path
