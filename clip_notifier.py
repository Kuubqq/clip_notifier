#!/usr/bin/env python3
"""
ClipNotifier – monitor schowka (wersja gotowa do pakowania z ikoną)
------------------------------------------------------------------
• Działa bez konsoli; po uruchomieniu pojawia się ikona w zasobniku systemowym.
• Kliknięcie prawym przyciskiem umożliwia zakończenie programu.
• Przy każdym kopiowaniu (Ctrl+C, menu itp.) wyświetla się chwilowy komunikat
  „Skopiowano!” na środku ekranu.
• Wczytuje ikonę z pliku **clipboard.png / clipboard.ico** – dzięki temu po
  spakowaniu np. PyInstallerem aplikacja zachowuje własną ikonę.
"""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path

import pyperclip
import pystray
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import ttk

# ───────────────────────────────────────── Ustawienia ──────────────────────────
POLL_INTERVAL = 0.2      # sekundy pomiędzy kolejnymi odczytami schowka
POPUP_LIFETIME = 1200    # czas wyświetlania popupu w ms

# Gdzie szukać zasobów (gdy aplikacja jest spakowana PyInstallerem, MEIPASS)
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
ICON_PATH = next((BASE_DIR / name for name in ("clipboard.png", "clipboard.ico") if (BASE_DIR / name).exists()), None)


class ClipNotifier:
    """Główna klasa monitorująca schowek i zarządzająca UI."""

    def __init__(self) -> None:
        # Tkinter działa jedynie jako silnik do wyświetlania popupów
        self.root = tk.Tk()
        self.root.withdraw()

        self.running = True
        self._last_clip: str = self._safe_paste()

        # Zamykanie sygnałami (użyteczne przy uruchomieniu z terminala)
        for _sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(_sig, lambda *_: self.stop())

        # Ikona w tray’u w osobnym wątku, żeby nie blokować pętli Tk
        self.icon = self._create_tray_icon()
        threading.Thread(target=self.icon.run, daemon=True).start()

        # Start monitorowania schowka
        self._poll_clipboard()

        # Główna pętla Tkinter (blokuje w tym miejscu aż do wyjścia)
        self.root.mainloop()

    # ────────────────────────────── Schowek ────────────────────────────────
    def _safe_paste(self) -> str:
        """Bezpieczne pobieranie tekstu ze schowka."""
        try:
            return pyperclip.paste()
        except pyperclip.PyperclipException:
            return ""

    def _poll_clipboard(self) -> None:
        if not self.running:
            return
        clip = self._safe_paste()
        if clip != self._last_clip:
            self._last_clip = clip
            self._show_popup()
        self.root.after(int(POLL_INTERVAL * 1000), self._poll_clipboard)

    # ────────────────────────────── UI: Popup ──────────────────────────────
    def _show_popup(self) -> None:
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        ttk.Label(
            popup,
            text="Skopiowano!",
            padding=(30, 15),
            font=("Arial", 14, "bold"),
            background="#333",
            foreground="#fff",
        ).pack()

        popup.update_idletasks()
        w, h = popup.winfo_width(), popup.winfo_height()
        sw, sh = popup.winfo_screenwidth(), popup.winfo_screenheight()
        popup.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        popup.after(POPUP_LIFETIME, popup.destroy)

    # ────────────────────────────── UI: Tray ───────────────────────────────
    def _generate_fallback_icon(self) -> Image.Image:
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle([(8, 8), (56, 56)], 8, outline="black", width=6)
        draw.rounded_rectangle([(20, 20), (44, 44)], 4, fill="black")
        return image

    def _create_tray_icon(self) -> pystray.Icon:
        if ICON_PATH and ICON_PATH.exists():
            try:
                image = Image.open(ICON_PATH)
                if image.size != (64, 64):  # standaryzujemy rozmiar
                    image = image.resize((64, 64), Image.LANCZOS)
            except Exception:
                image = self._generate_fallback_icon()
        else:
            image = self._generate_fallback_icon()

        menu = pystray.Menu(pystray.MenuItem("Wyjdź", lambda _: self.stop()))
        return pystray.Icon("ClipNotifier", image, "ClipNotifier", menu)

    # ────────────────────────────── Zamykanie ──────────────────────────────
    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        try:
            self.icon.stop()
        except Exception:
            pass
        self.root.quit()


# ────────────────────────────────────────── main ───────────────────────────────────────────

def main() -> None:  # pragma: no cover
    ClipNotifier()


if __name__ == "__main__":
    main()
