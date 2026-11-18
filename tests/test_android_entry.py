import json
import logging
import re
from pathlib import Path

import pytest

import android_entry
from controllers.api import Api
from models import history
from services import providers

VALID = {"api_type": "openai", "base_url": "https://a.example/v1",
         "api_key": "k-test", "model": "m1"}
UNCLEAR = json.dumps({"status": "unclear", "question": "Was?",
                      "options": [{"label": "Text"}, {"label": "Code"}]})


@pytest.fixture(autouse=True)
def _cleanup_logging(tmp_path):
    """Entfernt FileHandler unter tmp_path vom Root-Logger (Windows-Dateisperre)."""
    root = logging.getLogger()
    level = root.level
    yield
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler) and tmp_path in Path(h.baseFilename).parents:
            root.removeHandler(h)
            h.close()
    root.setLevel(level)


def call(api, method, *args):
    out = android_entry.dispatch(api, method, json.dumps(list(args)))
    assert isinstance(out, str)
    return json.loads(out)


# --- create_api ---------------------------------------------------------------

def test_create_api_files_and_settings(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    assert isinstance(api, Api)
    assert (tmp_path / "history.db").exists()
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / "app.log").exists()
    assert api.get_settings()["ok"] is True


def test_no_webview_or_paths_import():
    src = Path(android_entry.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+webview", src, re.M)
    assert "services.paths" not in src and "import paths" not in src


# --- dispatch -----------------------------------------------------------------

@pytest.mark.parametrize("method", ["nope", "_resolve", "_step", "__init__", ""])
def test_dispatch_unknown_method(tmp_path, method):
    api = android_entry.create_api(str(tmp_path))
    out = android_entry.dispatch(api, method, "[]")
    assert json.loads(out) == {"ok": False, "error": "Unbekannte Methode."}


@pytest.mark.parametrize("args_json", ["{kaputt", "", '{"a":1}', "1", '"x"', "null"])
def test_dispatch_invalid_input(tmp_path, args_json):
    api = android_entry.create_api(str(tmp_path))
    out = android_entry.dispatch(api, "get_settings", args_json)
    assert json.loads(out) == {"ok": False, "error": "Ungueltige Eingabe."}


def test_dispatch_roundtrip_get_settings(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    res = call(api, "get_settings")
    assert res["ok"] is True
    assert res["complete"] is False


def test_dispatch_save_then_complete(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    assert call(api, "save_settings", VALID) == {"ok": True}
    res = call(api, "get_settings")
    assert res["ok"] is True and res["complete"] is True
    assert "k-test" not in json.dumps(res)


def test_dispatch_wrong_arg_count(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    res = call(api, "get_settings", 1, 2)
    assert res == {"ok": False, "error": "Interner Fehler (TypeError)."}


def test_dispatch_exception_in_handler(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    res = call(api, "history_get", "abc")
    assert res["ok"] is False and res["error"] == "Interner Fehler (ValueError)."


def test_dispatch_choose_index_str(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    call(api, "save_settings", VALID)
    db = tmp_path / "history.db"
    sid = history.create_session(db, "roh", "openai", "m1")
    history.add_turn(db, sid, "assistant", UNCLEAR)
    res = call(api, "optimize_choose", sid, "0")
    assert res == {"ok": False, "error": "Ungueltige Auswahl."}


# --- Theme --------------------------------------------------------------------

def test_dispatch_set_theme_dark(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    assert call(api, "set_theme", "dark")["ok"] is True
    assert android_entry.get_theme(str(tmp_path)) == "dark"


def test_get_theme_default_without_env(tmp_path):
    assert android_entry.get_theme(str(tmp_path)) == "system"
    assert not (tmp_path / ".env").exists()


# --- Layout -------------------------------------------------------------------

def test_dispatch_get_settings_layout_default_fokus(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    assert call(api, "get_settings")["layout"] == "fokus"
    assert not (tmp_path / ".env").exists()


def test_dispatch_set_layout_roundtrip(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    assert call(api, "set_layout", "werkbank") == {"ok": True}
    assert call(api, "get_settings")["layout"] == "werkbank"
    assert call(api, "set_layout", "fokus") == {"ok": True}
    assert call(api, "get_settings")["layout"] == "fokus"


def test_dispatch_set_layout_invalid(tmp_path):
    api = android_entry.create_api(str(tmp_path))
    assert call(api, "set_layout", "kachel") == {"ok": False, "error": "Ungueltiges Layout."}
    assert call(api, "get_settings")["layout"] == "fokus"


def test_open_url_not_dispatchable(tmp_path):
    """Android oeffnet den Repo-Link nativ (PyBridge.open_url), nie ueber Python."""
    api = android_entry.create_api(str(tmp_path))
    assert call(api, "open_url", "https://github.com/Nope-im-not-pro/PromptEngineer") == {
        "ok": False, "error": "Unbekannte Methode."}


# --- Logging ------------------------------------------------------------------

def test_logging_error_to_app_log(tmp_path):
    android_entry.create_api(str(tmp_path))
    logging.getLogger("t").error("probe")
    logging.getLogger("t").warning("leise")
    text = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "probe" in text
    assert "leise" not in text


def test_logging_no_key_or_prompt(tmp_path, monkeypatch):
    api = android_entry.create_api(str(tmp_path))
    call(api, "save_settings", VALID)

    def boom(*a, **k):
        raise RuntimeError("k-test GEHEIM-PROMPT")

    monkeypatch.setattr(providers, "chat", boom)
    res = call(api, "optimize_start", "GEHEIM-PROMPT")
    assert res == {"ok": False, "error": "Interner Fehler (RuntimeError)."}
    logging.getLogger("t").error("probe")
    text = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "probe" in text
    assert VALID["api_key"] not in text
    assert "k-test" not in text and "GEHEIM-PROMPT" not in text
