import json
import re

import httpx
import pytest

from controllers.api import Api
from models import history
from services import settings

KEY = "sk-secret-STORED-1234"
CLEAR = json.dumps({"status": "clear", "optimized_prompt": "Optimiert"})
UNCLEAR = json.dumps({
    "status": "unclear",
    "question": "Was soll entstehen?",
    "options": [{"label": "Text", "description": "Fliesstext"}, {"label": "Code"}],
})


class FakeLLM:
    """MockTransport-Handler: Modellliste + Chat-Antworten der Reihe nach."""

    def __init__(self, *answers, models=("m-b", "m-a"), status=200):
        self.answers = list(answers)
        self.models = list(models)
        self.status = status
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={})
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": m} for m in self.models]})
        text = self.answers.pop(0)
        return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self))


def make_api(tmp_path, fake=None):
    client = fake.client() if fake else None
    return Api(tmp_path / ".env", tmp_path / "history.db", client=client)


def store(tmp_path, **kw):
    s = settings.Settings(**{"api_type": "openai", "base_url": "https://a.example/v1",
                             "api_key": KEY, "model": "m1", **kw})
    settings.save(tmp_path / ".env", s)
    return s


def env_text(tmp_path):
    return (tmp_path / ".env").read_text(encoding="utf-8")


# --- Grundstruktur ----------------------------------------------------------

def test_no_public_attributes_and_no_files(tmp_path):
    api = make_api(tmp_path, FakeLLM())
    assert [a for a in vars(api) if not a.startswith("_")] == []
    assert list(tmp_path.iterdir()) == []


def test_no_webview_import():
    import controllers.api as mod
    src = open(mod.__file__, encoding="utf-8").read()
    assert not re.search(r"^\s*(import|from)\s+webview", src, re.M)


def test_internal_exception_returns_error_dict(tmp_path):
    store(tmp_path)

    def boom(request):
        raise RuntimeError("kaputt")

    api = Api(tmp_path / ".env", tmp_path / "history.db",
              client=httpx.Client(transport=httpx.MockTransport(boom)))
    res = api.optimize_start("mach was")
    assert res["ok"] is False and isinstance(res["error"], str) and res["error"]
    res = api.list_models({"api_type": "openai", "base_url": "https://a.example/v1"})
    assert res["ok"] is False


def test_bad_input_returns_error_dict(tmp_path):
    api = make_api(tmp_path)
    for res in (api.save_settings(None), api.list_models("x"), api.history_get("abc"),
                api.optimize_choose("x", "y")):
        assert res["ok"] is False and res["error"]


# --- get_settings -----------------------------------------------------------

def test_get_settings_empty(tmp_path):
    res = make_api(tmp_path).get_settings()
    assert res["ok"] is True and res["complete"] is False
    assert res["settings"]["has_key"] is False and res["settings"]["key_hint"] == ""
    assert list(tmp_path.iterdir()) == []


def test_get_settings_hides_key(tmp_path):
    store(tmp_path)
    res = make_api(tmp_path).get_settings()
    assert KEY not in json.dumps(res)
    assert res["complete"] is True
    assert res["settings"] == {"api_type": "openai", "base_url": "https://a.example/v1",
                               "model": "m1", "has_key": True, "key_hint": "****1234"}


# --- Theme ------------------------------------------------------------------

def test_get_settings_theme_default_system(tmp_path):
    res = make_api(tmp_path).get_settings()
    assert res["theme"] == "system"
    assert set(res) == {"ok", "settings", "complete", "theme", "layout"}
    assert list(tmp_path.iterdir()) == []


def test_set_theme_dark_roundtrip_settings_unchanged(tmp_path):
    store(tmp_path)
    api = make_api(tmp_path)
    before = api.get_settings()
    assert api.set_theme("dark") == {"ok": True}
    after = api.get_settings()
    assert after["theme"] == "dark"
    assert after["settings"] == before["settings"] and after["complete"] is True
    assert KEY not in json.dumps(after)


def test_theme_does_not_affect_complete(tmp_path):
    api = make_api(tmp_path)
    assert api.set_theme("light") == {"ok": True}
    res = api.get_settings()
    assert res["theme"] == "light" and res["complete"] is False
    assert res["settings"]["has_key"] is False


@pytest.mark.parametrize("theme", ["blau", 1, None, "", ["dark"]])
def test_set_theme_invalid(tmp_path, theme):
    api = make_api(tmp_path)
    assert api.set_theme(theme) == {"ok": False, "error": "Ungueltiger Darstellungsmodus."}
    assert list(tmp_path.iterdir()) == []
    api.set_theme("dark")
    assert api.set_theme(theme)["ok"] is False
    assert api.get_settings()["theme"] == "dark"


# --- Layout -----------------------------------------------------------------

def test_get_settings_layout_default_desktop(tmp_path):
    res = make_api(tmp_path).get_settings()
    assert res["layout"] == "werkbank"
    assert list(tmp_path.iterdir()) == []


def test_get_settings_layout_default_android(tmp_path):
    api = Api(tmp_path / ".env", tmp_path / "history.db", platform="android")
    assert api.get_settings()["layout"] == "fokus"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("platform", ["desktop", "android"])
@pytest.mark.parametrize("layout", ["werkbank", "fokus"])
def test_set_layout_roundtrip_settings_and_theme_unchanged(tmp_path, platform, layout):
    store(tmp_path)
    api = Api(tmp_path / ".env", tmp_path / "history.db", platform=platform)
    api.set_theme("dark")
    before = api.get_settings()
    assert api.set_layout(layout) == {"ok": True}
    after = api.get_settings()
    assert after["layout"] == layout
    assert after["theme"] == "dark"
    assert after["settings"] == before["settings"] and after["complete"] is True
    assert KEY not in json.dumps(after)


@pytest.mark.parametrize("layout", ["kachel", 1, None, "", ["fokus"], "Fokus"])
def test_set_layout_invalid(tmp_path, layout):
    api = make_api(tmp_path)
    assert api.set_layout(layout) == {"ok": False, "error": "Ungueltiges Layout."}
    assert list(tmp_path.iterdir()) == []
    api.set_layout("fokus")
    assert api.set_layout(layout)["ok"] is False
    assert api.get_settings()["layout"] == "fokus"


def test_layout_invalid_text_differs_from_theme_text():
    from controllers import api as mod
    assert mod.LAYOUT_INVALID != mod.THEME_INVALID


# --- Repo-Link --------------------------------------------------------------

def test_open_url_repo_opens_browser(tmp_path, monkeypatch):
    import controllers.api as mod
    opened = []
    monkeypatch.setattr(mod.webbrowser, "open", lambda url: opened.append(url) or True)
    assert make_api(tmp_path).open_url("https://github.com/Nope-im-not-pro/PromptEngineer") == {"ok": True}
    assert opened == ["https://github.com/Nope-im-not-pro/PromptEngineer"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("url", [
    "https://example.com/", "https://github.com/Nope-im-not-pro/PromptEngineer/",
    "http://github.com/Nope-im-not-pro/PromptEngineer",
    "https://github.com/Nope-im-not-pro/PromptEngineer?x=1", "file:///etc/passwd",
    "javascript:alert(1)", "", None, 1, ["https://github.com/Nope-im-not-pro/PromptEngineer"],
])
def test_open_url_other_url_rejected(tmp_path, monkeypatch, url):
    import controllers.api as mod
    opened = []
    monkeypatch.setattr(mod.webbrowser, "open", lambda u: opened.append(u) or True)
    assert make_api(tmp_path).open_url(url) == {"ok": False, "error": "Link nicht erlaubt."}
    assert opened == []


def test_open_url_browser_failure(tmp_path, monkeypatch):
    import controllers.api as mod
    monkeypatch.setattr(mod.webbrowser, "open", lambda url: False)
    res = make_api(tmp_path).open_url(mod.REPO_URL)
    assert res == {"ok": False, "error": "Browser konnte nicht geoeffnet werden."}


# --- save_settings ----------------------------------------------------------

def test_save_settings_new(tmp_path):
    api = make_api(tmp_path)
    res = api.save_settings({"api_type": "openai", "base_url": "https://a.example/v1",
                             "api_key": "k-new", "model": "m1"})
    assert res == {"ok": True}
    assert settings.load(tmp_path / ".env").api_key == "k-new"


def test_save_empty_key_same_host_keeps_key(tmp_path):
    store(tmp_path)
    res = make_api(tmp_path).save_settings(
        {"api_type": "openai", "base_url": "https://a.example/v1/", "api_key": "", "model": "m2"})
    assert res["ok"] is True
    s = settings.load(tmp_path / ".env")
    assert s.api_key == KEY and s.model == "m2"


def test_save_invalid_data_env_unchanged(tmp_path):
    store(tmp_path)
    before = env_text(tmp_path)
    res = make_api(tmp_path).save_settings(
        {"api_type": "openai", "base_url": "ftp://x", "api_key": "", "model": ""})
    assert res["ok"] is False
    assert "Basis-URL" in res["error"] and "Modell" in res["error"]
    assert env_text(tmp_path) == before


def test_save_empty_key_other_host_openai_clears(tmp_path):
    store(tmp_path)
    res = make_api(tmp_path).save_settings(
        {"api_type": "openai", "base_url": "https://b.example/v1", "api_key": "", "model": "m1"})
    assert res["ok"] is True
    assert settings.load(tmp_path / ".env").api_key == ""
    assert KEY not in env_text(tmp_path)


def test_save_empty_key_other_host_anthropic_error(tmp_path):
    store(tmp_path, api_type="anthropic", base_url="https://a.example")
    before = env_text(tmp_path)
    res = make_api(tmp_path).save_settings(
        {"api_type": "anthropic", "base_url": "https://b.example", "api_key": "", "model": "m1"})
    assert res["ok"] is False and "API-Key" in res["error"]
    assert env_text(tmp_path) == before


def test_save_clear_key_openai(tmp_path):
    store(tmp_path)
    res = make_api(tmp_path).save_settings(
        {"api_type": "openai", "base_url": "https://a.example/v1", "api_key": "k-other",
         "model": "m1", "clear_key": True})
    assert res["ok"] is True
    assert settings.load(tmp_path / ".env").api_key == ""


def test_save_clear_key_anthropic_error(tmp_path):
    store(tmp_path, api_type="anthropic", base_url="https://a.example")
    before = env_text(tmp_path)
    res = make_api(tmp_path).save_settings(
        {"api_type": "anthropic", "base_url": "https://a.example", "api_key": "k-other",
         "model": "m1", "clear_key": True})
    assert res["ok"] is False
    assert env_text(tmp_path) == before


# --- list_models ------------------------------------------------------------

def test_list_models_uses_stored_key_same_host(tmp_path):
    store(tmp_path)
    fake = FakeLLM()
    res = make_api(tmp_path, fake).list_models(
        {"api_type": "openai", "base_url": "https://a.example/v1", "api_key": ""})
    assert res == {"ok": True, "models": ["m-a", "m-b"]}
    assert fake.requests[0].headers["authorization"] == f"Bearer {KEY}"


def test_list_models_other_host_no_stored_key(tmp_path):
    store(tmp_path)
    fake = FakeLLM()
    res = make_api(tmp_path, fake).list_models(
        {"api_type": "openai", "base_url": "https://evil.example/v1", "api_key": ""})
    assert res["ok"] is True
    assert len(fake.requests) == 1
    for req in fake.requests:
        assert KEY not in json.dumps(dict(req.headers))
        assert "authorization" not in req.headers


def test_list_models_anthropic_without_key_no_network(tmp_path):
    store(tmp_path, api_type="anthropic", base_url="https://a.example")
    fake = FakeLLM()
    res = make_api(tmp_path, fake).list_models(
        {"api_type": "anthropic", "base_url": "https://b.example", "api_key": ""})
    assert res["ok"] is False and "API-Key" in res["error"]
    assert fake.requests == []


def test_list_models_provider_error(tmp_path):
    fake = FakeLLM(status=401)
    res = make_api(tmp_path, fake).list_models(
        {"api_type": "openai", "base_url": "https://a.example/v1", "api_key": "k"})
    assert res["ok"] is False and "401" in res["error"]


# --- history_* --------------------------------------------------------------

def test_history_list_get_delete(tmp_path):
    db = tmp_path / "history.db"
    history.init_db(db)
    sid = history.create_session(db, "roh", "openai", "m1")
    history.add_turn(db, sid, "user", "roh")
    api = make_api(tmp_path)
    res = api.history_list()
    assert res["ok"] is True and [i["id"] for i in res["items"]] == [sid]
    res = api.history_get(sid)
    assert res["ok"] is True and res["item"]["turns"] == [{"role": "user", "content": "roh"}]
    assert api.history_delete(sid) == {"ok": True}
    assert api.history_get(sid)["ok"] is False
    assert api.history_delete(sid)["ok"] is False
    assert api.history_list()["items"] == []


# --- Workflow ---------------------------------------------------------------

def test_workflow_a_unclear_choose_clear(tmp_path):
    store(tmp_path)
    fake = FakeLLM(UNCLEAR, CLEAR)
    api = make_api(tmp_path, fake)
    res = api.optimize_start("mach was")
    assert res["ok"] is True and res["result"]["status"] == "unclear"
    sid = res["session_id"]
    res = api.optimize_choose(sid, 1)
    assert res == {"ok": True, "result": {"status": "clear", "optimized_prompt": "Optimiert"}}
    item = api.history_get(sid)["item"]
    assert item["status"] == "done" and item["optimized_prompt"] == "Optimiert"
    assert [t["role"] for t in item["turns"]] == ["user", "assistant", "user", "assistant"]
    assert "Code" in item["turns"][2]["content"]
    sent = json.loads(fake.requests[-1].content)["messages"]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]


def test_workflow_b_refine_loop(tmp_path):
    store(tmp_path)
    fake = FakeLLM(UNCLEAR, UNCLEAR, CLEAR)
    api = make_api(tmp_path, fake)
    sid = api.optimize_start("mach was")["session_id"]
    res = api.optimize_refine(sid, "mach Text")
    assert res["ok"] is True and res["result"]["status"] == "unclear"
    res = api.optimize_refine(sid, "mach Text ueber X")
    assert res["result"]["status"] == "clear"
    item = api.history_get(sid)["item"]
    assert item["status"] == "done" and len(item["turns"]) == 6
    sent = json.loads(fake.requests[-1].content)["messages"]
    assert len(sent) == 6  # system + 5


def test_workflow_c_start_clear(tmp_path):
    store(tmp_path)
    api = make_api(tmp_path, FakeLLM(CLEAR))
    res = api.optimize_start("schreibe Gedicht ueber Herbst")
    assert res["result"] == {"status": "clear", "optimized_prompt": "Optimiert"}
    item = api.history_get(res["session_id"])["item"]
    assert item["status"] == "done" and item["raw_prompt"] == "schreibe Gedicht ueber Herbst"


def test_workflow_d_choose_invalid_index(tmp_path):
    store(tmp_path)
    fake = FakeLLM(UNCLEAR)
    api = make_api(tmp_path, fake)
    sid = api.optimize_start("mach was")["session_id"]
    for idx in (2, -1, "a", None):
        res = api.optimize_choose(sid, idx)
        assert res["ok"] is False and res["error"]
    assert len(fake.requests) == 1
    assert len(api.history_get(sid)["item"]["turns"]) == 2


def test_workflow_e_incomplete_settings_no_network(tmp_path):
    fake = FakeLLM(CLEAR)
    api = make_api(tmp_path, fake)
    res = api.optimize_start("mach was")
    assert res["ok"] is False and "Einstellungen" in res["error"]
    assert fake.requests == []
    assert not (tmp_path / "history.db").exists()


def test_workflow_f_provider_error_keeps_session_open(tmp_path):
    store(tmp_path)
    fake = FakeLLM(UNCLEAR)
    api = make_api(tmp_path, fake)
    sid = api.optimize_start("mach was")["session_id"]
    fake.status = 500
    res = api.optimize_choose(sid, 0)
    assert res["ok"] is False and "500" in res["error"]
    res = api.optimize_refine(sid, "neu")
    assert res["ok"] is False
    item = api.history_get(sid)["item"]
    assert item["status"] == "open" and len(item["turns"]) == 2


def test_start_provider_error_creates_no_session(tmp_path):
    store(tmp_path)
    api = make_api(tmp_path, FakeLLM(status=429))
    res = api.optimize_start("mach was")
    assert res["ok"] is False and "429" in res["error"]
    assert api.history_list()["items"] == []


def test_protocol_error_returns_error(tmp_path):
    store(tmp_path)
    api = make_api(tmp_path, FakeLLM("kein json", "immer noch nicht"))
    res = api.optimize_start("mach was")
    assert res["ok"] is False and res["error"]
    assert api.history_list()["items"] == []


def test_unknown_session(tmp_path):
    store(tmp_path)
    fake = FakeLLM(CLEAR)
    api = make_api(tmp_path, fake)
    assert api.optimize_refine(999, "x")["ok"] is False
    assert api.optimize_choose(999, 0)["ok"] is False
    assert fake.requests == []
