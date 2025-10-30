from __future__ import annotations

import json
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any, Tuple

from .macro_store import MacroStore
from ..utils.openProgramm import openProgramm


class ReplayError(Exception):
    pass


_SCREENSHOT_RE = re.compile(r"screenshot_(\d+)_([-\d]+)_([-\d]+)\.png$", re.IGNORECASE)


def _parse_name(fname: str) -> Optional[Tuple[int, int, int]]:
    m = _SCREENSHOT_RE.search(fname)
    if not m:
        return None
    ts = int(m.group(1)); x = int(m.group(2)); y = int(m.group(3))
    return ts, x, y


class ReplayService:
    """
    Startet optional zuerst ein 'startup_program' aus meta.json und erst DANN den Macro-Client.
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
        self.program_launcher = openProgramm()

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

        # Ordner sicherstellen
        (macro_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        (macro_dir / "results").mkdir(parents=True, exist_ok=True)

        # ---- NEU: Startup-Programm VOR dem Macro öffnen ----
        self._maybe_start_startup_program(macro_dir)

        # Actions-Datei normalisieren (Icons)
        fixed_actions = self._prepare_actions_file(macro_dir, actions)

        # Inline-Runner für macro_replay.py
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

    def _maybe_start_startup_program(self, macro_dir: Path) -> None:
        """
        Liest meta.json und startet 'extra.startup_program' (z.B. "Word") VOR dem Replay.
        Wartet kurz, damit Fenster öffnen können.
        """
        meta_file = macro_dir / "meta.json"
        if not meta_file.exists():
            return
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            startup_program = meta.get("extra", {}).get("startup_program")
            if startup_program and isinstance(startup_program, str) and startup_program.strip():
                print(f"[ReplayService] Starting program before replay: {startup_program}", flush=True)
                # versucht, die App zu starten; Fehler sind nicht fatal fürs Replay
                try:
                    ok = self.program_launcher.run([startup_program])
                    if ok:
                        # kleine Gnadenfrist: App-Fenster darf aufgehen
                        time.sleep(1.0)
                except Exception as e:
                    print(f"[ReplayService] Fehler beim Starten von '{startup_program}': {e}", flush=True)
        except Exception as e:
            print(f"[ReplayService] Error reading meta.json for startup_program: {e}", flush=True)

    def _find_client_dir(self) -> Path:
        here = Path(__file__).resolve()
        desktop_dir = here.parents[3]       # .../Desktop
        dashboard_dir = here.parents[2]     # .../Desktop/Dashboard
        python_dir = desktop_dir.parent     # .../Python

        candidates = [
            desktop_dir / "Makro-Client",
            python_dir / "Makro-Client",
            dashboard_dir.parent / "Makro-Client",
        ]
        for c in candidates:
            if c.exists():
                return c
        tried = " | ".join(str(c) for c in candidates)
        raise ReplayError(f"Makro-Client nicht gefunden. Versuchte Pfade: {tried}")

    # -------- actions.log -> actions.fixed.log mit Pfad-Resolver --------

    def _prepare_actions_file(self, macro_dir: Path, actions_path: Path) -> Path:
        fixed_path = macro_dir / "actions.fixed.log"
        screenshots_dir = macro_dir / "screenshots"

        all_pngs = sorted(screenshots_dir.glob("*.png"))
        by_xy: Dict[Tuple[int, int], List[Tuple[int, Path]]] = {}
        by_ts: List[Tuple[int, Path]] = []
        fallback_blank = screenshots_dir / "screenshot_.png"

        for p in all_pngs:
            meta = _parse_name(p.name)
            if not meta:
                if p.name.lower() == "screenshot_.png":
                    continue
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
            return f"screenshots/{p.name}"

        def resolve_icon(requested_path: str) -> str:
            abs_req = Path(requested_path)
            if abs_req.exists():
                try:
                    abs_req.relative_to(screenshots_dir)
                    return rel_in_screenshots(abs_req)
                except Exception:
                    return abs_req.as_posix()

            candidate = screenshots_dir / abs_req.name
            if candidate.exists():
                return rel_in_screenshots(candidate)

            meta = _parse_name(abs_req.name)
            if meta:
                ts, x, y = meta
                lst = by_xy.get((x, y), [])
                p = nearest_by_ts(ts, lst)
                if p:
                    return rel_in_screenshots(p)
                p = nearest_by_ts(ts, by_ts)
                if p:
                    return rel_in_screenshots(p)

            if fallback_blank.exists():
                return rel_in_screenshots(fallback_blank)

            if all_pngs:
                return rel_in_screenshots(all_pngs[0])

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
