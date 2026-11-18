"""Android-Einstieg: Api-Instanz, Logging, JSON-Dispatch fuer die WebView-Bruecke."""
import json
import logging
from pathlib import Path

from controllers.api import Api
from models import history
from services import settings

ALLOWED = {"get_settings", "save_settings", "list_models", "optimize_start",
           "optimize_choose", "optimize_refine", "history_list", "history_get",
           "history_delete", "set_theme", "set_layout"}


def create_api(files_dir: str) -> Api:
    base = Path(files_dir)
    handler = logging.FileHandler(base / "app.log", delay=True, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.ERROR, handlers=[handler], force=True)
    history.init_db(base / "history.db")
    return Api(base / ".env", base / "history.db", platform="android")


def dispatch(api: Api, method: str, args_json: str) -> str:
    if method not in ALLOWED:
        return json.dumps({"ok": False, "error": "Unbekannte Methode."})
    try:
        args = json.loads(args_json)
    except ValueError:
        return json.dumps({"ok": False, "error": "Ungueltige Eingabe."})
    if not isinstance(args, list):
        return json.dumps({"ok": False, "error": "Ungueltige Eingabe."})
    return json.dumps(getattr(api, method)(*args))


def get_theme(files_dir: str) -> str:
    return settings.load_theme(Path(files_dir) / ".env")
