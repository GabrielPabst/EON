# app/utils/win_windows.py
from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import List, Tuple

IS_WIN = sys.platform.startswith("win")
if IS_WIN:
    import ctypes
    from ctypes import wintypes

@dataclass
class WindowInfo:
    hwnd: int
    title: str
    pid: int
    exe: str
    rect: Tuple[int, int, int, int]  # (l, t, r, b)

def enumerate_app_windows(show_all: bool = False, limit: int = 18) -> List[WindowInfo]:
    """Return filtered top-level app windows; dedup by (pid,title)."""
    if not IS_WIN:
        return []

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    dwmapi = ctypes.windll.dwmapi

    GetWindowTextLengthW = user32.GetWindowTextLengthW
    GetWindowTextW = user32.GetWindowTextW
    GetWindowRect = user32.GetWindowRect
    IsWindowVisible = user32.IsWindowVisible
    IsIconic = user32.IsIconic
    GetAncestor = user32.GetAncestor
    GA_ROOTOWNER = 3
    GetClassNameW = user32.GetClassNameW
    GetWindowLongW = user32.GetWindowLongW
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x80
    WS_EX_APPWINDOW = 0x40000
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId

    # dwm cloaked?
    DWMWA_CLOAKED = 14

    # exe path
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    rows: List[WindowInfo] = []
    seen = set()

    def _enum(hWnd, _):
        try:
            if not IsWindowVisible(hWnd) or IsIconic(hWnd):
                return True
            if GetAncestor(hWnd, GA_ROOTOWNER) != hWnd:
                return True

            ex = GetWindowLongW(hWnd, GWL_EXSTYLE)
            if (ex & WS_EX_TOOLWINDOW) and not (ex & WS_EX_APPWINDOW):
                return True

            cloaked = wintypes.UINT(0)
            if hasattr(dwmapi, "DwmGetWindowAttribute"):
                dwmapi.DwmGetWindowAttribute(hWnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if cloaked.value:
                    return True

            n = GetWindowTextLengthW(hWnd)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            GetWindowTextW(hWnd, buf, n + 1)
            title = buf.value.strip()
            if not title:
                return True

            rc = wintypes.RECT()
            GetWindowRect(hWnd, ctypes.byref(rc))
            w, h = rc.right - rc.left, rc.bottom - rc.top
            if not show_all and (w < 240 or h < 160):
                return True

            cls = ctypes.create_unicode_buffer(256)
            GetClassNameW(hWnd, cls, 256)
            if not show_all and cls.value in {"Progman", "Shell_TrayWnd", "ToolTips_Class32"}:
                return True

            pid = wintypes.DWORD()
            GetWindowThreadProcessId(hWnd, ctypes.byref(pid))
            exe = ""
            hProc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if hProc:
                try:
                    size = wintypes.DWORD(32768)
                    pbuf = ctypes.create_unicode_buffer(size.value)
                    if QueryFullProcessImageNameW(hProc, 0, pbuf, ctypes.byref(size)):
                        exe = pbuf.value
                finally:
                    kernel32.CloseHandle(hProc)

            key = (pid.value, title)
            if key in seen:
                return True
            seen.add(key)

            rows.append(WindowInfo(int(hWnd), title, int(pid.value), exe, (rc.left, rc.top, rc.right, rc.bottom)))
        except Exception:
            pass
        return True

    EnumWindows(EnumWindowsProc(_enum), 0)

    try:
        fg = user32.GetForegroundWindow()
    except Exception:
        fg = 0

    def area(r: Tuple[int, int, int, int]) -> int:
        l, t, rgt, btm = r
        return max(1, (rgt - l) * (btm - t))

    rows.sort(key=lambda wi: (wi.hwnd != fg, -area(wi.rect)))
    return rows if show_all else rows[:limit]

def grab_window_preview(hwnd: int, max_width: int = 360):
    """Best-effort QPixmap for a window using PrintWindow; BitBlt fallback. Returns None on failure."""
    if not (IS_WIN and hwnd):
        return None
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage, QPixmap

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        rc = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rc)):
            return None
        w, h = rc.right - rc.left, rc.bottom - rc.top
        if w <= 0 or h <= 0:
            return None

        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        gdi32.SelectObject(hdc_mem, hbmp)

        PW_RENDERFULLCONTENT = 0x00000002
        ok = user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)
        if not ok:
            SRCCOPY = 0x00CC0020
            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, rc.left, rc.top, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
            ]
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER); bmi.biWidth = w; bmi.biHeight = -h
        bmi.biPlanes = 1; bmi.biBitCount = 32; bmi.biCompression = 0

        buf = (ctypes.c_ubyte * (w * h * 4))()
        gdi32.GetDIBits(hdc_mem, hbmp, 0, h, ctypes.byref(buf), ctypes.byref(bmi), 0)

        gdi32.DeleteObject(hbmp); gdi32.DeleteDC(hdc_mem); user32.ReleaseDC(0, hdc_screen)

        img = QImage(bytes(buf), w, h, QImage.Format.Format_RGBA8888).copy()
        pm = QPixmap.fromImage(img)
        return pm.scaledToWidth(max_width, Qt.SmoothTransformation) if w > max_width else pm
    except Exception:
        return None
