from __future__ import annotations
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
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]


def open_browser() -> None:
    for _ in range(60):
        try:
            urllib.request.urlopen(URL + "api/meta", timeout=1)
            break
        except OSError:
            time.sleep(0.5)
    else:
        print(f"Server not responding, open {URL} manually")
        return

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