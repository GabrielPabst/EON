# app/services/hotkey_service.py
from __future__ import annotations
from typing import Callable, Dict, Optional

# Backend A: 'keyboard' (bevorzugt auf Windows, global und oft am zuverlässigsten)
try:
    import keyboard as kb  # type: ignore
    KB_AVAILABLE = True
except Exception:
    KB_AVAILABLE = False

# Backend B: 'pynput' (Fallback, wenn 'keyboard' nicht verfügbar ist)
if not KB_AVAILABLE:
    from pynput import keyboard  # type: ignore


def _expand_user_spec(spec: Optional[str]) -> Optional[str]:
    """
    Aus einer Kurzangabe (z.B. 'k') wird unsere Standard-Kombi:
    '<ctrl>+<shift>+<alt>+k'.
    Vollständige Spezifikationen bleiben unverändert.
    """
    if not spec:
        return None
    s = spec.strip().lower()
    if len(s) == 1 and s.isalnum():
        return f"<ctrl>+<shift>+<alt>+{s}"
    return s


def _canon_for_keyboard_module(expanded: str) -> str:
    """
    'keyboard' erwartet 'ctrl+shift+alt+k' (ohne spitze Klammern).
    """
    return (
        expanded.replace("<ctrl>", "ctrl")
        .replace("<shift>", "shift")
        .replace("<alt>", "alt")
        .replace("<cmd>", "windows")
        .replace(" ", "")
    )


class HotkeyService:
    """
    Nutzungs-API:
      set_macro_hotkey(macro_id, 'k')  -> registriert Ctrl+Shift+Alt+K
      set_stop_hotkey('<ctrl>+<shift>+<alt>+s')

    Callbacks:
      on_start_request(macro_id: str)
      on_stop_request()
    """

    def __init__(self) -> None:
        self.on_start_request: Optional[Callable[[str], None]] = None
        self.on_stop_request: Optional[Callable[[], None]] = None

        self.backend: str = "keyboard" if KB_AVAILABLE else "pynput"

        # Gemeinsame Daten
        self._macro_specs: Dict[str, Optional[str]] = {}   # user value: Buchstabe oder None
        self._stop_spec: Optional[str] = None

        # keyboard-Backend Handles
        self._kb_handles: Dict[str, Optional[int]] = {}
        self._kb_stop_handle: Optional[int] = None

        # pynput-Backend
        self._pn_listener = None  # type: ignore

        print(f"[HK] HotkeyService init – Backend: {self.backend} "
              f"(keyboard available: {KB_AVAILABLE})")

    # ---------------- Lifecycle ----------------
    def start(self) -> None:
        print(f"[HK] start() – Backend {self.backend}")
        if self.backend == "keyboard":
            # keyboard startet "on demand", kein Listener, nichts zu tun
            return
        self._rebuild_pynput()

    def stop(self) -> None:
        print(f"[HK] stop() – Backend {self.backend}")
        if self.backend == "keyboard":
            try:
                for macro_id, h in list(self._kb_handles.items()):
                    if h is not None:
                        kb.remove_hotkey(h)  # type: ignore
                        print(f"[HK] (keyboard) removed hotkey for {macro_id}")
            except Exception as ex:
                print(f"[HK] (keyboard) remove_hotkey error: {ex}")
            self._kb_handles.clear()
            if self._kb_stop_handle is not None:
                try:
                    kb.remove_hotkey(self._kb_stop_handle)  # type: ignore
                    print("[HK] (keyboard) removed STOP hotkey")
                except Exception as ex:
                    print(f"[HK] (keyboard) remove STOP error: {ex}")
            self._kb_stop_handle = None
            return

        # pynput
        if self._pn_listener is not None:
            try:
                self._pn_listener.stop()
                print("[HK] (pynput) listener stopped")
            except Exception as ex:
                print(f"[HK] (pynput) stop error: {ex}")
            self._pn_listener = None

    # ---------------- Public API ----------------
    def set_macro_hotkey(self, macro_id: str, combo_spec: Optional[str]) -> None:
        """combo_spec ist bei uns üblicherweise nur ein Buchstabe ('k')."""
        print(f"[HK] set_macro_hotkey({macro_id!r}, {combo_spec!r})")
        self._macro_specs[macro_id] = combo_spec

        if self.backend == "keyboard":
            # vorhandenen entfernen
            old = self._kb_handles.get(macro_id)
            if old is not None:
                try:
                    kb.remove_hotkey(old)  # type: ignore
                    print(f"[HK] (keyboard) removed previous hotkey for {macro_id}")
                except Exception as ex:
                    print(f"[HK] (keyboard) remove previous error: {ex}")
                self._kb_handles[macro_id] = None

            # neuen registrieren
            if combo_spec:
                expanded = _expand_user_spec(combo_spec) or ""
                seq = _canon_for_keyboard_module(expanded)
                try:
                    handle = kb.add_hotkey(seq, lambda mid=macro_id: self._fire_start(mid))  # type: ignore
                    self._kb_handles[macro_id] = handle
                    print(f"[HK] (keyboard) registered {seq} -> start {macro_id}")
                except Exception as ex:
                    print(f"[HK] (keyboard) add_hotkey error for {seq}: {ex}")
            else:
                print(f"[HK] (keyboard) no hotkey set for {macro_id}")
            return

        # pynput: kompletten Listener neu aufbauen
        self._rebuild_pynput()

    def set_stop_hotkey(self, combo: Optional[str]) -> None:
        print(f"[HK] set_stop_hotkey({combo!r})")
        self._stop_spec = combo

        if self.backend == "keyboard":
            if self._kb_stop_handle is not None:
                try:
                    kb.remove_hotkey(self._kb_stop_handle)  # type: ignore
                    print("[HK] (keyboard) removed old STOP hotkey")
                except Exception as ex:
                    print(f"[HK] (keyboard) remove old STOP error: {ex}")
                self._kb_stop_handle = None

            if combo:
                seq = _canon_for_keyboard_module(combo)
                try:
                    self._kb_stop_handle = kb.add_hotkey(seq, self._fire_stop)  # type: ignore
                    print(f"[HK] (keyboard) registered STOP: {seq}")
                except Exception as ex:
                    print(f"[HK] (keyboard) add STOP error for {seq}: {ex}")
            else:
                print("[HK] (keyboard) STOP hotkey disabled")
            return

        self._rebuild_pynput()

    # ---------------- Intern ----------------
    def _fire_start(self, macro_id: str) -> None:
        print(f"[HK] TRIGGER start -> {macro_id}")
        if self.on_start_request:
            try:
                self.on_start_request(macro_id)
            except Exception as ex:
                print(f"[HK] on_start_request error: {ex}")

    def _fire_stop(self) -> None:
        print("[HK] TRIGGER stop")
        if self.on_stop_request:
            try:
                self.on_stop_request()
            except Exception as ex:
                print(f"[HK] on_stop_request error: {ex}")

    # ----- pynput-spezifisch -----
    def _rebuild_pynput(self) -> None:
        if self.backend != "pynput":
            return

        # alten Listener beenden
        if self._pn_listener is not None:
            try:
                self._pn_listener.stop()
                print("[HK] (pynput) listener replaced")
            except Exception as ex:
                print(f"[HK] (pynput) stop (replace) error: {ex}")
            self._pn_listener = None

        mapping: Dict[str, Callable[[], None]] = {}
        for mid, spec in self._macro_specs.items():
            if not spec:
                continue
            expanded = _expand_user_spec(spec)
            if not expanded:
                continue
            mapping[expanded] = (lambda m=mid: self._fire_start(m))
        if self._stop_spec:
            mapping[self._stop_spec] = self._fire_stop

        if not mapping:
            print("[HK] (pynput) nothing to register")
            return

        try:
            self._pn_listener = keyboard.GlobalHotKeys(mapping)  # type: ignore
            self._pn_listener.start()
            print(f"[HK] (pynput) registered hotkeys: {list(mapping.keys())}")
        except Exception as ex:
            self._pn_listener = None
            print(f"[HK] (pynput) GlobalHotKeys error: {ex}")
