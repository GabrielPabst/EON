import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# pywin32 ist optional – nur verwenden, wenn vorhanden (für .lnk-Auflösung)
try:
    import win32com.client  # type: ignore
    _HAS_WIN32 = True
except Exception:
    win32com = None  # type: ignore
    _HAS_WIN32 = False


class openProgramm:
    """
    Windows-Programm-Launcher:
    - Lädt bekannte Pfade aus knownPaths.json (robust, mehrere Suchpfade)
    - Erweitert %USERNAME% usw.
    - Versucht außerdem: shutil.which(), where.exe, Startmenü-Shortcuts (.lnk), Registry
    """

    # Startmenü-Locations (werden mit expandvars() erweitert)
    COMMON_INSTALL_LOCATIONS = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        r"C:\Users\%USERNAME%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
    ]

    def __init__(self, known_paths_filename: str = "knownPaths.json") -> None:
        self.KNOWN_APPS: dict[str, str] = {}
        self._load_known_apps(known_paths_filename)

        # gängige Synonyme -> Schlüssel der JSON (alles lower)
        self._alias = {
            "word": "microsoft word",
            "excel": "microsoft excel",
            "powerpoint": "microsoft powerpoint",
            "vscode": "visual studio code",
            "vs code": "visual studio code",
            "chrome": "google chrome",
            "edge": "microsoft edge",
            "firefox": "mozilla firefox",
        }

    # ---------- public API ----------

    def run(self, params: list[str]) -> bool:
        """
        Erwartet params[0] als App-Name (z. B. "Word" oder "google chrome").
        Gibt True/False zurück (Erfolg).
        """
        if not params:
            print("[openProgramm] Kein App-Name übergeben.")
            return False

        app_name = (params[0] or "").strip().lower()
        if not app_name:
            print("[openProgramm] App-Name leer.")
            return False

        # Alias-Mapping
        app_key = self._alias.get(app_name, app_name)
        return self.open_application(app_key)

    def open_application(self, app_name: str) -> bool:
        """
        Findet und öffnet eine Anwendung. Liefert True bei Erfolg.
        """
        path = self.get_installation_path(app_name)
        if not path:
            print(f"[openProgramm] Anwendung '{app_name}' nicht gefunden.")
            return False

        path = os.path.expandvars(path)
        # Wenn Pfad in Anführungszeichen kommt oder Argumente enthält, lassen wir os.startfile
        # den normalen Weg gehen – ansonsten subprocess.
        try:
            if os.path.isfile(path):
                # .exe direkt starten
                print(f"[openProgramm] Öffne: {path}")
                os.startfile(path)  # type: ignore[attr-defined]
                return True

            # Es könnte ein zusammengesetzter String sein: "C:\...\app.exe" --arg
            # Versuchen, Target + Args zu splitten:
            m = re.match(r'^\s*"([^"]+)"\s*(.*)$', path)
            if m and os.path.isfile(m.group(1)):
                exe = m.group(1)
                args = m.group(2).strip()
                print(f"[openProgramm] Öffne: {exe} {args}")
                subprocess.Popen([exe] + ([args] if args else []), shell=False)
                return True

            # Letzter Versuch: vielleicht ist es ein Ordner/URL/Verknüpfung – os.startfile kann das.
            print(f"[openProgramm] Öffne via Shell: {path}")
            os.startfile(path)  # type: ignore[attr-defined]
            return True
        except Exception as e:
            print(f"[openProgramm] Fehler beim Öffnen: {e}")
            return False

    # ---------- path resolution ----------

    def get_installation_path(self, app_name: str) -> Optional[str]:
        """
        Sucht nach einem Pfad zu 'app_name':
          1) knownPaths.json
          2) shutil.which()
          3) where.exe
          4) Startmenü-Shortcuts (.lnk)
          5) Registry (DisplayName/DisplayIcon/InstallLocation)
        """
        print(f"[openProgramm] Suche nach '{app_name}' ...")

        # 1) Known apps
        if app_name in self.KNOWN_APPS:
            p = os.path.expandvars(self.KNOWN_APPS[app_name])
            print(f"[openProgramm] Known app: {p}")
            return p

        # 2) which()
        p = shutil.which(app_name)
        if p:
            print(f"[openProgramm] Gefunden via which(): {p}")
            return p

        # 3) where.exe
        p = self._get_install_path_from_where(app_name)
        if p:
            print(f"[openProgramm] Gefunden via where.exe: {p}")
            return p

        # 4) Startmenü durchsuchen
        p = self._search_common_install_paths(app_name)
        if p:
            print(f"[openProgramm] Gefunden via Startmenü: {p}")
            return p

        # 5) Registry
        p = self._get_install_path_from_registry(app_name)
        if p:
            print(f"[openProgramm] Gefunden via Registry: {p}")
            return p

        return None

    # ---------- internals ----------

    def _load_known_apps(self, filename: str) -> None:
        """
        Lädt knownPaths.json robust:
          - neben dieser Datei (./knownPaths.json)
          - eine Ebene höher
          - zwei Ebenen höher
          - aktuelles Arbeitsverzeichnis
        """
        here = Path(__file__).resolve()
        candidates = [
            here.parent / filename,                 # .../app/utils/knownPaths.json
            here.parent.parent / filename,          # .../app/knownPaths.json
            here.parent.parent.parent / filename,   # .../knownPaths.json (Projektwurzel)
            Path.cwd() / filename                   # aktuelles Arbeitsverzeichnis
        ]

        data = None
        for c in candidates:
            try:
                if c.exists():
                    with c.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        print(f"[openProgramm] knownPaths geladen: {c}")
                        break
            except Exception as e:
                print(f"[openProgramm] Fehler beim Laden {c}: {e}")

        if not isinstance(data, dict):
            data = {"known_applications": {}}

        known = data.get("known_applications") or {}
        # %USERNAME% expandieren
        username = os.getenv("USERNAME") or ""
        for k, v in known.items():
            v = str(v).replace("%USERNAME%", username)
            self.KNOWN_APPS[k.strip().lower()] = v

    def _get_install_path_from_where(self, app_name: str) -> Optional[str]:
        try:
            # falls which nichts findet, noch where.exe probieren
            r = subprocess.run(["where", app_name],
                               capture_output=True, text=True, check=True)
            paths = [p.strip() for p in r.stdout.splitlines() if p.strip()]
            return paths[0] if paths else None
        except Exception:
            return None

    def _resolve_shortcut(self, shortcut_path: str) -> Optional[str]:
        """
        .lnk -> Ziel inkl. Arguments, wenn möglich.
        """
        try:
            if not _HAS_WIN32:
                return None
            shell = win32com.client.Dispatch("WScript.Shell")  # type: ignore
            sc = shell.CreateShortcut(shortcut_path)
            target = sc.TargetPath or ""
            args = sc.Arguments or ""
            if target:
                if args:
                    return f'"{target}" {args}'.strip()
                return target
        except Exception:
            pass
        return None

    def _search_common_install_paths(self, app_name: str) -> Optional[str]:
        try:
            for base in self.COMMON_INSTALL_LOCATIONS:
                base_dir = os.path.expandvars(base)
                if not os.path.exists(base_dir):
                    continue
                for root, _, files in os.walk(base_dir):
                    for file in files:
                        if file.lower().endswith(".lnk") and app_name.lower() in file.lower():
                            sp = os.path.join(root, file)
                            resolved = self._resolve_shortcut(sp)
                            if resolved:
                                return resolved
        except Exception:
            pass
        return None

    def _get_install_path_from_registry(self, app_name: str) -> Optional[str]:
        """
        Sucht per Registry nach DisplayName & liefert InstallLocation / DisplayIcon.
        """
        try:
            import winreg  # nur bei Bedarf
        except Exception:
            return None

        reg_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        def _val_or_none(key, name):
            try:
                v, _ = winreg.QueryValueEx(key, name)
                return v
            except Exception:
                return None

        for root, path in reg_roots:
            try:
                with winreg.OpenKey(root, path) as reg:
                    count = winreg.QueryInfoKey(reg)[0]
                    for i in range(count):
                        try:
                            skn = winreg.EnumKey(reg, i)
                            with winreg.OpenKey(reg, skn) as sk:
                                disp = _val_or_none(sk, "DisplayName")
                                if not disp or app_name.lower() not in disp.lower():
                                    continue

                                inst = _val_or_none(sk, "InstallLocation")
                                icon = _val_or_none(sk, "DisplayIcon")

                                # Bevorzugt ein .exe
                                for cand in (icon, inst):
                                    if not cand:
                                        continue
                                    cand = str(cand).strip().strip('"')
                                    if os.path.isdir(cand):
                                        # Versuche, darin eine .exe zu finden
                                        exe = self._find_exe_in_dir(cand)
                                        if exe:
                                            return exe
                                    if os.path.isfile(cand):
                                        return cand
                        except Exception:
                            continue
            except Exception:
                continue
        return None

    def _find_exe_in_dir(self, d: str) -> Optional[str]:
        try:
            for name in os.listdir(d):
                if name.lower().endswith(".exe"):
                    return os.path.join(d, name)
        except Exception:
            pass
        return None
