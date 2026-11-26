"""Starts the app for development: the server with auto-reload, and the browser once the assistant
is ready. `--no-browser` keeps the browser closed; PORT picks the port."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", "8000"))
URL = f"http://{HOST}:{PORT}/"

CHROME_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
]


def assistant_ready() -> bool | None:
    """True/False once the server answers (is the startup warm-up done?), None while it doesn't."""
    try:
        with urllib.request.urlopen(URL + "api/ready", timeout=2) as resp:
            return bool(json.loads(resp.read()).get("assistant_ready", True))
    except (OSError, ValueError):
        return None


def open_browser() -> None:
    # Wait for the warm-up (~15-30 s), not just for the server: otherwise the page opens at once and the
    # first chat still waits for the libraries to load. After 2 minutes open anyway (the page shows the state).
    printed = False
    for _ in range(120):
        ready = assistant_ready()
        if ready:
            if printed:
                print(f"Assistant ready, opening {URL}")
            break
        if ready is False and not printed:
            print("Starting the assistant, the browser opens when it's ready...")
            printed = True
        time.sleep(1)
    else:
        print(f"The assistant isn't ready yet, opening {URL} anyway")

    chrome = next((p for p in CHROME_PATHS if os.path.exists(p)), None)
    if chrome:
        webbrowser.register("chrome", None, webbrowser.BackgroundBrowser(chrome))
        webbrowser.get("chrome").open(URL)
    else:
        webbrowser.open(URL)

if __name__ == "__main__":
    if "--no-browser" not in sys.argv:
        threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
