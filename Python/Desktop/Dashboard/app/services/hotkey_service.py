from __future__ import annotations
from typing import Callable, Dict, Optional, Set, Tuple
import threading

from pynput import keyboard
from pynput.keyboard import Key, KeyCode


CanonicalCombo = Tuple[str, ...]  # z.B. ("<ctrl>", "<alt>", "p")


def _canon_key(k) -> Optional[str]:
    """
    Normalisiert pynput-Key/KeyCode zu Strings:
      - linke/rechte Modifier -> "<ctrl>", "<alt>", "<shift>", "<cmd>"
      - Buchstaben/Ziffern -> "a", "1"
      - F-Tasten -> "f1".."f24"
      - Sondertasten -> "enter", "tab", "esc", ...
    """
    # KeyCode (buchstabe/zeichen)
    if isinstance(k, KeyCode):
        if k.char:
            return k.char.lower()
        return None

    # Key.* (inkl. ctrl_l/ctrl_r)
    if isinstance(k, Key):
        name = str(k).split('.')[-1]  # z.B. 'ctrl_l', 'enter'
        # Modifiers vereinheitlichen
        if name in ("ctrl", "ctrl_l", "ctrl_r"):
            return "<ctrl>"
        if name in ("alt", "alt_l", "alt_r"):
            return "<alt>"
        if name in ("shift", "shift_l", "shift_r"):
            return "<shift>"
        if name in ("cmd", "cmd_l", "cmd_r", "win"):
            return "<cmd>"
        # F-Tasten
        if name.startswith("f") and name[1:].isdigit():
            return name
        return name
    return None


def _parse_combo(spec: Optional[str]) -> Optional[CanonicalCombo]:
    """
    Parse "<ctrl>+<alt>+p" | "f8" | "<win>+f2" | "enter" etc. -> kanonische Tuple.
    Leer/None -> None.
    """
    if not spec:
        return None
    s = spec.strip().lower()
    if not s:
        return None

    parts = [p.strip() for p in s.replace(" ", "").split("+") if p.strip()]
    mapped: list[str] = []
    for p in parts:
        if p in ("<ctrl>", "<control>", "<ctl>"):
            mapped.append("<ctrl>")
        elif p in ("<alt>",):
            mapped.append("<alt>")
        elif p in ("<shift>",):
            mapped.append("<shift>")
        elif p in ("<cmd>", "<win>", "<meta>"):
            mapped.append("<cmd>")
        elif p.startswith("f") and p[1:].isdigit():
            mapped.append(p)  # f1..f24
        else:
            # Key.enter -> enter ; sonst einzelnes zeichen
            if p.startswith("key."):
                mapped.append(p.split(".", 1)[1])
            else:
                mapped.append(p)
    # doppelte entfernen & sortieren (reihenfolge-unabhängig)
    dedup = sorted(set(mapped))
    return tuple(dedup) if dedup else None


class HotkeyService:
    """
    Globaler Hotkey-Listener mit frei definierbaren Kombis pro Makro.
    - set_macro_hotkey(macro_id, "<ctrl>+<alt>+p")
    - set_stop_hotkey("<ctrl>+<alt>+s")
    Callbacks:
      on_start_request(macro_id)
      on_stop_request()
    """

    def __init__(self) -> None:
        self.on_start_request: Optional[Callable[[str], None]] = None
        self.on_stop_request: Optional[Callable[[], None]] = None

        self._macro_hotkeys: Dict[str, Optional[CanonicalCombo]] = {}  # id -> combo
        self._stop_combo: Optional[CanonicalCombo] = None

        self._pressed: Set[str] = set()
        self._fired: Set[CanonicalCombo] = set()

        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ---------- public API ----------
    def start(self) -> None:
        if self._running:
            return
        self._running = True

        def run():
            with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as li:
                self._listener = li
                li.join()

        self._thread = threading.Thread(target=run, name="HotkeyListener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._thread = None

    def set_macro_hotkey(self, macro_id: str, combo: Optional[str]) -> None:
        with self._lock:
            self._macro_hotkeys[macro_id] = _parse_combo(combo)

    def set_stop_hotkey(self, combo: Optional[str]) -> None:
        with self._lock:
            self._stop_combo = _parse_combo(combo)

    # ---------- intern ----------
    def _combo_matches(self, required: CanonicalCombo) -> bool:
        # Treffer, wenn alle erforderlichen Tasten gedrückt sind (weitere dürfen zusätzlich gedrückt sein)
        return set(required).issubset(self._pressed)

    def _on_press(self, key):
        k = _canon_key(key)
        if not k:
            return
        with self._lock:
            self._pressed.add(k)

            # Stop zuerst prüfen
            if self._stop_combo and self._combo_matches(self._stop_combo) and self._stop_combo not in self._fired:
                self._fired.add(self._stop_combo)
                if self.on_stop_request:
                    try: self.on_stop_request()
                    except Exception: pass
                return

            # Start-Hotkeys prüfen
            for mid, combo in list(self._macro_hotkeys.items()):
                if not combo:
                    continue
                if combo in self._fired:
                    continue
                if self._combo_matches(combo):
                    self._fired.add(combo)
                    if self.on_start_request:
                        try: self.on_start_request(mid)
                        except Exception: pass

    def _on_release(self, key):
        k = _canon_key(key)
        if not k:
            return
        with self._lock:
            # Taste loslassen
            if k in self._pressed:
                self._pressed.remove(k)
            # Gefeuerten-Status zurücksetzen, sobald eine an der Kombi beteiligte Taste losgelassen wird
            to_clear = set()
            for combo in self._fired:
                if k in combo:
                    to_clear.add(combo)
            self._fired.difference_update(to_clear)
