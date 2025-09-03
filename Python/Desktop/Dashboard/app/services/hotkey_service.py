# app/services/hotkey_service.py
from __future__ import annotations

import time
import threading
from typing import Callable, Dict, Optional

try:
    from pynput import keyboard
except Exception:
    keyboard = None  # erlaubt Headless/CI

_LOG_PREFIX = "[HK]"

def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", flush=True)


class HotkeyService:
    """
    Global-Hotkeys via pynput.GlobalHotKeys

    - Standard: <ctrl>+<shift>+<alt> + <key/combination>
    - set_macro_hotkey(macro_id, key_or_combo)  # 'k' oder '<f5>' etc.
    - set_stop_hotkey(combo)                    # z.B. '<ctrl>+<shift>+<alt>+s'

    Extras:
      * Debounce (250 ms) gegen Doppel-Trigger
      * Release klemmender Modifiers vor Callback (Ctrl/Shift/Alt/AltGr/Cmd)
      * UI-Dispatcher: Optionaler Callable, der Funktionen sicher in den UI-Thread bringt.
        -> per set_ui_dispatcher(fn) vom MainWindow setzen, z.B. QTimer.singleShot(0, fn)
    """

    def __init__(self) -> None:
        self.on_start_request: Optional[Callable[[str], None]] = None
        self.on_stop_request: Optional[Callable[[], None]] = None

        self._macro_map: Dict[str, str] = {}   # macro_id -> key_or_combo
        self._stop_combo: Optional[str] = None

        self._listener: Optional["keyboard.GlobalHotKeys"] = None
        self._last_trigger_ms: float = 0.0
        self._debounce_ms: int = 250

        self._kb_controller = None
        if keyboard is not None:
            try:
                self._kb_controller = keyboard.Controller()
            except Exception:
                self._kb_controller = None

        self._ui_dispatch: Optional[Callable[[Callable[[], None]], None]] = None
        self._running = False

    # ---------- Public API ----------

    def start(self) -> None:
        self._running = True
        self._rebuild_listener()

    def stop(self) -> None:
        self._running = False
        self._stop_listener()

    def set_ui_dispatcher(self, dispatcher: Optional[Callable[[Callable[[], None]], None]]) -> None:
        """
        dispatcher(fn) -> führt fn im UI-Thread aus (vom MainWindow gesetzt).
        Beispiel (PySide6):
            hotkeys.set_ui_dispatcher(lambda fn: QTimer.singleShot(0, fn))
        """
        self._ui_dispatch = dispatcher
        _log(f"ui_dispatcher set: {'yes' if dispatcher else 'none'}")

    def set_stop_hotkey(self, combo: Optional[str]) -> None:
        self._stop_combo = combo or None
        _log(f"set_stop_hotkey({repr(combo)})")
        self._rebuild_listener()

    def set_macro_hotkey(self, macro_id: str, key_or_combo: Optional[str]) -> None:
        if key_or_combo:
            self._macro_map[macro_id] = key_or_combo
        else:
            self._macro_map.pop(macro_id, None)
        _log(f"set_macro_hotkey('{macro_id}', {repr(key_or_combo)})")
        self._rebuild_listener()

    # ---------- Internals ----------

    def _stop_listener(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _rebuild_listener(self) -> None:
        self._stop_listener()

        if not self._running or keyboard is None:
            _log("(pynput) nothing to register")
            return

        combo_map: Dict[str, Callable[[], None]] = {}
        if self._stop_combo:
            combo_map[self._stop_combo] = self._on_stop

        for mid, key in self._macro_map.items():
            combo_map[self._with_base(key)] = self._make_start_cb(mid)

        if not combo_map:
            _log("(pynput) nothing to register")
            return

        try:
            self._listener = keyboard.GlobalHotKeys(combo_map)
            self._listener.start()
            _log("(pynput) listener replaced")
            _log("(pynput) registered hotkeys: " + str(sorted(combo_map.keys())))
        except Exception as e:
            _log(f"(pynput) failed to start listener: {e!r}")

    def _with_base(self, key_or_combo: str) -> str:
        k = key_or_combo.strip()
        if k.startswith("<") and k.endswith(">"):
            return f"<ctrl>+<shift>+<alt>+{k.lower()}"
        return f"<ctrl>+<shift>+<alt>+{k.lower()}"

    def _debounced(self) -> bool:
        now = time.monotonic() * 1000.0
        if now - self._last_trigger_ms < self._debounce_ms:
            return True
        self._last_trigger_ms = now
        return False

    def _make_start_cb(self, macro_id: str) -> Callable[[], None]:
        def _cb() -> None:
            if self._debounced():
                return
            _log(f"TRIGGER start -> {macro_id} (cb={'set' if self.on_start_request else 'none'})")
            self._release_modifiers_async()

            def invoke():
                _log(f"CALL start_cb on UI thread? {'yes' if self._ui_dispatch else 'no (direct)'}")
                try:
                    if self.on_start_request:
                        self.on_start_request(macro_id)
                    else:
                        _log("WARN: on_start_request not set")
                except Exception as ex:
                    _log(f"ERROR in on_start_request: {ex!r}")

            if self._ui_dispatch:
                try:
                    self._ui_dispatch(invoke)
                except Exception as ex:
                    _log(f"ERROR in ui_dispatch: {ex!r}; falling back to thread")
                    threading.Thread(target=invoke, daemon=True).start()
            else:
                threading.Thread(target=invoke, daemon=True).start()

        return _cb

    def _on_stop(self) -> None:
        if self._debounced():
            return
        _log("TRIGGER stop")
        self._release_modifiers_async()

        def invoke():
            _log("CALL stop_cb")
            try:
                if self.on_stop_request:
                    self.on_stop_request()
                else:
                    _log("WARN: on_stop_request not set")
            except Exception as ex:
                _log(f"ERROR in on_stop_request: {ex!r}")

        if self._ui_dispatch:
            try:
                self._ui_dispatch(invoke)
            except Exception as ex:
                _log(f"ERROR in ui_dispatch(stop): {ex!r}; fallback thread")
                threading.Thread(target=invoke, daemon=True).start()
        else:
            threading.Thread(target=invoke, daemon=True).start()

    # ---------- Modifier-Freigabe ----------

    def _release_modifiers_async(self) -> None:
        if self._kb_controller is None or keyboard is None:
            return

        def _worker():
            try:
                time.sleep(0.03)  # OS den Hotkey verarbeiten lassen
                keys = []
                try:
                    keys += [
                        keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                        keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
                        keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                    ]
                except Exception:
                    pass
                try:
                    keys += [keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r]
                except Exception:
                    pass
                for k in keys:
                    try:
                        self._kb_controller.release(k)
                    except Exception:
                        pass
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
