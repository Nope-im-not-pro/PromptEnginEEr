"""App-Einstieg: Fenster + js_api starten; --selftest prueft Build ohne Laufzeitdateien."""
import argparse
import logging
import os
import sqlite3
import sys
import tempfile
import threading
import time

import webview

from controllers.api import Api
from models import history
from services import paths

TITLE = "Prompt EnginEEr"
MIN_SIZE = (800, 600)
RUNTIME_FILES = (".env", "history.db", "app.log")
SELFTEST_TIMEOUT = 90
_result = {"code": 1}


def _index_url() -> str:
    return str(paths.resource_dir() / "static" / "index.html")


def _wait_ready(window, timeout: float) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if window.evaluate_js("document.getElementById('app').dataset.ready || ''") == "1":
            return True
        time.sleep(0.2)
    return False


def _eval_promise(window, script: str, timeout: float = 15):
    """evaluate_js loest Promises nur mit Callback auf."""
    box, done = {}, threading.Event()

    def cb(value):
        box["value"] = value
        done.set()

    window.evaluate_js(script, cb)
    return box.get("value") if done.wait(timeout) else None


def _app_dir_writable() -> bool:
    fd, tmp = tempfile.mkstemp(dir=paths.app_dir(), prefix="selftest_", suffix=".tmp")
    os.write(fd, b"x")
    os.close(fd)
    os.remove(tmp)
    return not os.path.exists(tmp)


def _selftest(window, existing: set) -> None:
    checks = {}
    try:
        checks["loaded"] = window.events.loaded.wait(30)
        checks["ready"] = _wait_ready(window, 30)
        checks["get_settings"] = _eval_promise(
            window, "window.pywebview.api.get_settings().then(r => r.ok === true)") is True
        checks["app_dir_writable"] = _app_dir_writable()
        con = sqlite3.connect(":memory:")
        checks["sqlite_memory"] = con.execute("select 1").fetchone() == (1,)
        con.close()
        created = {n for n in RUNTIME_FILES if (paths.app_dir() / n).exists()} - existing
        checks["no_runtime_files"] = not created
    except Exception:
        checks["exception"] = False
    _result["code"] = 0 if checks and all(checks.values()) else 1
    window.destroy()


def selftest() -> int:
    """Fenster hidden, kein Logging, keine DB-Datei; Exit-Code = Ergebnis."""
    existing = {n for n in RUNTIME_FILES if (paths.app_dir() / n).exists()}
    api = Api(paths.env_path(), paths.db_path())  # Init ruft nur get_settings (legt nichts an)
    window = webview.create_window(TITLE, url=_index_url(), js_api=api,
                                   min_size=MIN_SIZE, hidden=True)
    watchdog = threading.Timer(SELFTEST_TIMEOUT, lambda: os._exit(3))
    watchdog.daemon = True
    watchdog.start()
    webview.start(_selftest, (window, existing), http_server=True)
    return _result["code"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()

    handler = logging.FileHandler(paths.app_dir() / "app.log", delay=True, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.ERROR, handlers=[handler])

    history.init_db(paths.db_path())
    api = Api(paths.env_path(), paths.db_path())
    webview.create_window(TITLE, url=_index_url(), js_api=api, min_size=MIN_SIZE)
    webview.start(http_server=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
