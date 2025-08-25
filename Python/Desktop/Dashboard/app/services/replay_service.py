from __future__ import annotations
import sys
import signal
import subprocess
from pathlib import Path
from typing import Optional, Callable
from string import Template
from textwrap import dedent

from .macro_store import MacroStore


class ReplayError(Exception):
    pass


class ReplayService:
    def __init__(self, store: MacroStore, desktop_root: Optional[Path] = None) -> None:
        self.store = store
        self._proc: Optional[subprocess.Popen] = None
        self._running_id: Optional[str] = None
        self.on_started: Optional[Callable[[str], None]] = None
        self.on_finished: Optional[Callable[[str, Optional[str]], None]] = None

        # Makro-Client finden
        here = Path(__file__).resolve()
        desktop_dir = here.parents[3]
        dashboard_dir = here.parents[2]
        python_dir = desktop_dir.parent

        candidates = [
            desktop_dir / "Makro-Client",
            python_dir / "Makro-Client",
            dashboard_dir.parent / "Makro-Client",
        ]
        p = desktop_dir
        for _ in range(4):
            p = p.parent
            if p.name.lower() == "python":
                candidates.append(p / "Makro-Client")
                break

        self.makro_client_dir: Optional[Path] = next((c for c in candidates if c.exists()), None)
        if self.makro_client_dir is None:
            tried = " | ".join(str(c) for c in candidates)
            raise ReplayError(f"Makro-Client nicht gefunden. Versuchte Pfade: {tried}")
        if not (self.makro_client_dir / "macro_replay.py").exists():
            raise ReplayError(f"Makro-Client unvollständig: {self.makro_client_dir}\\macro_replay.py fehlt")

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

        tmpl = Template(dedent("""
            import sys, time, threading, json
            sys.path.insert(0, $CLIENT_DIR)

            import pyautogui
            pyautogui.FAILSAFE = False

            from pynput.mouse import Controller as MouseCtl, Button
            from pynput.keyboard import Controller as KeyCtl, Key, KeyCode
            from macro_replay import MacroReplayManager

            mouse = MouseCtl()
            keyboard = KeyCtl()

            def load_actions(path):
                evs = []
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line=line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            t = obj.get('time')
                            if t is None:
                                continue
                            typ = obj.get('type')
                            key = obj.get('key')

                            if typ in ('press','release') and isinstance(key, str) and key.startswith('mouse_Button.'):
                                btn_name = key.split('.',1)[1]
                                evs.append({'kind':'mouse_'+typ, 'button':btn_name, 'time':t})
                            elif typ == 'click':
                                btn = obj.get('button','left')
                                cnt = int(obj.get('count',1) or 1)
                                evs.append({'kind':'mouse_click', 'button':btn, 'count':cnt, 'time':t})
                            elif typ in ('press','release'):
                                evs.append({'kind':'key_'+typ, 'key':key, 'time':t})
                        except Exception:
                            pass
                return evs

            SPECIAL = {
                'enter':'enter','return':'enter','space':'space','tab':'tab',
                'esc':'esc','escape':'esc','backspace':'backspace','delete':'delete',
                'home':'home','end':'end','pageup':'page_up','pagedown':'page_down',
                'left':'left','right':'right','up':'up','down':'down'
            }

            def normalize_key_string(s: str) -> str:
                s = s.strip()
                if len(s) >= 2 and s[0] == s[-1] and s[0] in ('\"', \"'\"):
                    s = s[1:-1]  # Strip Quotes: "'q'" -> q
                return s

            def resolve_key(k):
                if isinstance(k, str):
                    s = normalize_key_string(k)
                    if s.startswith('Key.'):
                        name = s.split('.',1)[1]
                        return getattr(Key, name, None)
                    if s in SPECIAL:
                        return getattr(Key, SPECIAL[s], None)
                    if s.startswith('f') and s[1:].isdigit():
                        return getattr(Key, s, None)
                    if len(s) == 1:
                        return KeyCode.from_char(s)
                    return None
                return None

            def do_actions(events, start_time, first_event_time):
                events = sorted(events, key=lambda e: e['time'])
                for e in events:
                    target = (e['time'] - first_event_time)
                    now = time.perf_counter() - start_time
                    delay = target - now
                    if delay > 0:
                        time.sleep(delay)

                    kind = e['kind']
                    try:
                        if kind in ('mouse_press','mouse_release'):
                            btn = {'left':Button.left, 'right':Button.right, 'middle':Button.middle}.get(e.get('button','left'), Button.left)
                            if kind == 'mouse_press':
                                mouse.press(btn)
                            else:
                                mouse.release(btn)
                            print('[mouse]', kind, e.get('button'))
                        elif kind == 'mouse_click':
                            btn = {'left':Button.left, 'right':Button.right, 'middle':Button.middle}.get(e.get('button','left'), Button.left)
                            cnt = int(e.get('count',1) or 1)
                            for _ in range(cnt):
                                mouse.click(btn)
                            print('[mouse] click x'+str(cnt), e.get('button'))
                        elif kind in ('key_press','key_release'):
                            key_obj = resolve_key(e.get('key'))
                            if key_obj is None:
                                print('[key] unknown', e.get('key'))
                                continue
                            if kind == 'key_press':
                                keyboard.press(key_obj)
                            else:
                                keyboard.release(key_obj)
                            print('[key]', kind, e.get('key'))
                    except Exception as ex:
                        print('Action error:', ex)

            m = MacroReplayManager(mouse_log=$MOUSE_LOG, actions_log=$ACTIONS_LOG)
            mr = m.mouse_replay
            action_events = load_actions($ACTIONS_LOG)

            print('Using logs:'); print('  actions:', $ACTIONS_LOG); print('  mouse  :', $MOUSE_LOG)
            print('Precount -> moves:', len(mr.events), 'actions:', len(action_events))
            if not (mr.events or action_events):
                print('Keine Events gefunden.'); import sys; sys.exit(0)

            first_event_time = min(([e['time'] for e in mr.events] or [float('inf')]) +
                                   ([e['time'] for e in action_events] or [float('inf')]))
            start_time = time.perf_counter()

            t_moves = threading.Thread(target=mr.replay, args=(start_time, first_event_time), daemon=True)
            t_actions = threading.Thread(target=do_actions, args=(action_events, start_time, first_event_time), daemon=True)

            print('Replaying ...')
            t_moves.start(); t_actions.start()
            t_moves.join(); t_actions.join()
            print('Replay fertig.')
        """))

        inline = tmpl.substitute(
            CLIENT_DIR=repr(self.makro_client_dir.as_posix()),
            MOUSE_LOG=repr(moves.as_posix()),
            ACTIONS_LOG=repr(actions.as_posix()),
        )

        creation_flags = 0
        if sys.platform.startswith("win"):
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

        try:
            self._proc = subprocess.Popen(
                [sys.executable, "-c", inline],
                cwd=str(self.makro_client_dir),
                creationflags=creation_flags,
            )
            self._running_id = macro_id
            if self.on_started:
                try: self.on_started(macro_id)
                except Exception: pass
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
            try: self.on_finished(rid, err)
            except Exception: pass
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
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   capture_output=True, text=True)
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
                try: self.on_finished(rid, None)
                except Exception: pass
