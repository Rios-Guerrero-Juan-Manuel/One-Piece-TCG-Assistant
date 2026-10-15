"""Tiny launcher window for the Windows portable bundle.

Built into ``OnePieceTCGAssistant.exe`` with PyInstaller (``--onefile
--noconsole``). It only uses the standard library: it starts the bundled
embedded Python (``python\\pythonw.exe run_app.py``) as a hidden subprocess,
waits for the server URL file, opens the browser and offers a clean way to
stop the app.
"""

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path

IS_FROZEN = bool(getattr(sys, "frozen", False))

if IS_FROZEN:
    BUNDLE_ROOT = Path(sys.executable).resolve().parent
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent

PYTHON_EXE = BUNDLE_ROOT / "python" / "pythonw.exe"
RUN_APP = BUNDLE_ROOT / "run_app.py"
URL_WAIT_SECONDS = 180


def _data_dir() -> Path:
    override = os.environ.get("OPTCG_DATA_DIR", "").strip()
    if override:
        return Path(override)
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        return Path(local_app) / "OnePieceTCGAssistant"
    return BUNDLE_ROOT / "data"


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("One Piece TCG Assistant")
        self.root.geometry("420x190")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self.process: subprocess.Popen | None = None
        self.url: str | None = None
        self.browser_opened = False
        self._events: queue.Queue[tuple[str, str]] = queue.Queue()

        title = tk.Label(
            self.root,
            text="One Piece TCG Assistant",
            font=("Segoe UI", 14, "bold"),
            bg="#1a1a2e",
            fg="#e8a838",
        )
        title.pack(pady=(14, 4))

        self.status = tk.Label(
            self.root,
            text="Iniciando servidor...",
            font=("Segoe UI", 9),
            bg="#1a1a2e",
            fg="#c8c8d0",
        )
        self.status.pack(pady=(0, 10))

        buttons = tk.Frame(self.root, bg="#1a1a2e")
        buttons.pack(pady=4)

        self.open_btn = tk.Button(
            buttons,
            text="Abrir navegador",
            font=("Segoe UI", 10),
            width=16,
            state=tk.DISABLED,
            command=self._open_browser,
        )
        self.open_btn.pack(side=tk.LEFT, padx=6)

        self.quit_btn = tk.Button(
            buttons,
            text="Salir",
            font=("Segoe UI", 10),
            width=12,
            command=self._quit,
        )
        self.quit_btn.pack(side=tk.LEFT, padx=6)

        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self._start_server()
        threading.Thread(target=self._wait_for_url, daemon=True).start()
        self._poll_events()

    def _start_server(self) -> None:
        if not PYTHON_EXE.exists() or not RUN_APP.exists():
            self.status.config(
                text=f"Instalacion incompleta: falta {PYTHON_EXE.name} o run_app.py",
                fg="#ef4444",
            )
            return
        creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        try:
            self.process = subprocess.Popen(  # noqa: S603
                [str(PYTHON_EXE), str(RUN_APP)],
                cwd=str(BUNDLE_ROOT),
                creationflags=creationflags,
            )
        except OSError as exc:
            self.status.config(text=f"No se pudo iniciar: {exc}", fg="#ef4444")

    def _wait_for_url(self) -> None:
        url_file = _data_dir() / "app_url.txt"
        deadline = time.monotonic() + URL_WAIT_SECONDS
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                self._events.put(("status", ("El servidor se cerro inesperadamente", "#ef4444")))
                return
            if url_file.exists():
                try:
                    url = url_file.read_text(encoding="utf-8").strip()
                except OSError:
                    url = ""
                if url:
                    self.url = url
                    self._events.put(("status", (f"Servidor listo: {url}", "#22c55e")))
                    self._events.put(("ready", ""))
                    return
            time.sleep(1)
        self._events.put(("status", ("El servidor tardo demasiado en responder", "#f97316")))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self._events.get_nowait()
                if kind == "status":
                    text, color = value
                    self.status.config(text=text, fg=color)
                elif kind == "ready":
                    self.open_btn.config(state=tk.NORMAL)
                    self.root.after(300, self._open_browser)
        except queue.Empty:
            pass
        self.root.after(200, self._poll_events)

    def _open_browser(self) -> None:
        if not self.url:
            return
        self.browser_opened = True
        webbrowser.open(self.url)

    def _quit(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    LauncherApp().run()
