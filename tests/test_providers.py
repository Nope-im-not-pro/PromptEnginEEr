import json

import httpx
import pytest

from services import providers
from services.providers import ProviderError

KEY = "sk-SECRET-1234567890"


def make_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


# --- normalize_base_url -------------------------------------------------------

def test_normalize_openai_strips_trailing_slash():
    assert providers.normalize_base_url("openai", "https://x/v1/") == "https://x/v1"


@pytest.mark.parametrize("url", ["https://api.anthropic.com/v1/", "https://api.anthropic.com/v1",
                                 "https://api.anthropic.com/"])
def test_normalize_anthropic_strips_v1(url):
    assert providers.normalize_base_url("anthropic", url) == "https://api.anthropic.com"


# --- list_models --------------------------------------------------------------

def test_list_models_openai():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [{"id": "b"}, {"id": "a"}, {"id": "b"}]})

    models = providers.list_models("openai", "https://x/v1/", KEY, client=make_client(handler))
    assert models == ["a", "b"]
    assert str(seen[0].url) == "https://x/v1/models"
    assert seen[0].headers["authorization"] == f"Bearer {KEY}"


def test_list_models_openai_empty_key_no_auth_header():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [{"id": "llama"}]})

    assert providers.list_models("openai", "http://localhost:11434/v1", "",
                                 client=make_client(handler)) == ["llama"]
    assert "authorization" not in seen[0].headers


def test_list_models_anthropic_paging():
    seen = []

    def handler(request):
        seen.append(request)
        if "after_id" not in request.url.params:
            return httpx.Response(200, json={"data": [{"id": "m2"}], "has_more": True, "last_id": "m2"})
        return httpx.Response(200, json={"data": [{"id": "m1"}], "has_more": False, "last_id": "m1"})

    models = providers.list_models("anthropic", "https://api.anthropic.com/v1/", KEY,
                                   client=make_client(handler))
    assert models == ["m1", "m2"]
    assert len(seen) == 2
    first, second = seen
    assert first.url.path == "/v1/models"
    assert first.url.host == "api.anthropic.com"
    assert first.url.params["limit"] == "1000"
    assert second.url.params["after_id"] == "m2"
    for r in seen:
        assert r.headers["x-api-key"] == KEY
        assert r.headers["anthropic-version"] == "2023-06-01"
        assert "authorization" not in r.headers


# --- chat ---------------------------------------------------------------------

MSGS = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "a"},
        {"role": "user", "content": "b"}]


def test_chat_openai():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]})

    out = providers.chat("openai", "https://x/v1/", KEY, "gpt", "SYS", MSGS, client=make_client(handler))
    assert out == "ok"
    req = seen[0]
    assert str(req.url) == "https://x/v1/chat/completions"
    assert req.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(req.content)
    assert body["model"] == "gpt"
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    assert body["messages"][1:] == MSGS
    assert "temperature" not in body


def test_chat_openai_empty_key_no_auth_header():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    providers.chat("openai", "http://localhost:11434/v1", "", "m", "S", MSGS, client=make_client(handler))
    assert "authorization" not in seen[0].headers


def test_chat_anthropic():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"content": [
            {"type": "text", "text": "Hal"}, {"type": "thinking", "thinking": "x"},
            {"type": "text", "text": "lo"}]})

    out = providers.chat("anthropic", "https://api.anthropic.com/v1", KEY, "claude", "SYS", MSGS,
                         client=make_client(handler))
    assert out == "Hallo"
    req = seen[0]
    assert str(req.url) == "https://api.anthropic.com/v1/messages"
    assert req.headers["x-api-key"] == KEY
    assert req.headers["anthropic-version"] == "2023-06-01"
    body = json.loads(req.content)
    assert body == {"model": "claude", "max_tokens": 4096, "system": "SYS", "messages": MSGS}


# --- Fehlerfaelle -------------------------------------------------------------

def _status_handler(code):
    def handler(request):
        return httpx.Response(code, json={"error": f"bad key {KEY}"})
    return handler


def _raise(exc_cls):
    def handler(request):
        raise exc_cls(f"failed with {KEY}", request=request)
    return handler


ERROR_CASES = [
    ("401", _status_handler(401), 401),
    ("403", _status_handler(403), 403),
    ("404", _status_handler(404), 404),
    ("429", _status_handler(429), 429),
    ("500", _status_handler(500), 500),
    ("timeout", _raise(httpx.ReadTimeout), None),
    ("connect", _raise(httpx.ConnectError), None),
    ("nojson", lambda r: httpx.Response(200, text="<html>nope</html>"), None),
    ("structure", lambda r: httpx.Response(200, json={"foo": 1}), None),
]


@pytest.mark.parametrize("api_type", ["openai", "anthropic"])
@pytest.mark.parametrize("name,handler,status", ERROR_CASES, ids=[c[0] for c in ERROR_CASES])
@pytest.mark.parametrize("op", ["models", "chat"])
def test_errors(api_type, name, handler, status, op):
    client = make_client(handler)
    with pytest.raises(ProviderError) as ei:
        if op == "models":
            providers.list_models(api_type, "https://h/v1", KEY, client=client)
        else:
            providers.chat(api_type, "https://h/v1", KEY, "m", "S", MSGS, client=client)
    err = ei.value
    assert err.status == status
    assert err.user_message
    assert KEY not in err.user_message
    assert KEY not in str(err)
    assert KEY not in repr(err)


def test_error_messages_distinct_and_german():
    msgs = {}
    for name, handler, _ in ERROR_CASES:
        with pytest.raises(ProviderError) as ei:
            providers.chat("openai", "https://h/v1", KEY, "m", "S", MSGS, client=make_client(handler))
        msgs[name] = ei.value.user_message
    assert "Key" in msgs["401"] and "Key" in msgs["403"]
    assert "Modell" in msgs["404"]
    assert "Limit" in msgs["429"]
    assert "Server" in msgs["500"]
    assert "Zeit" in msgs["timeout"]
    assert "Verbindung" in msgs["connect"]
    assert len({msgs["timeout"], msgs["connect"], msgs["nojson"], msgs["404"], msgs["429"],
                msgs["500"]}) == 6


BAD_KEY = "sk-geheïm Schlüssel-987"


@pytest.mark.parametrize("api_type", ["openai", "anthropic"])
@pytest.mark.parametrize("op", ["models", "chat"])
def test_non_ascii_key_is_provider_error_without_leak(api_type, op):
    client = make_client(lambda r: httpx.Response(200, json={}))
    with pytest.raises(ProviderError) as ei:
        if op == "models":
            providers.list_models(api_type, "https://h/v1", BAD_KEY, client=client)
        else:
            providers.chat(api_type, "https://h/v1", BAD_KEY, "m", "S", MSGS, client=client)
    err = ei.value
    assert "ungueltige Zeichen" in err.user_message
    for text in (err.user_message, str(err), repr(err), repr(err.args)):
        assert BAD_KEY not in text
    assert err.__cause__ is None
    assert err.__context__ is None or err.__suppress_context__


@pytest.mark.parametrize("ids", [["m1", "m1"], ["a", "b", "a", "b"]], ids=["same", "cycle"])
def test_list_models_anthropic_paging_stops_on_repeated_last_id(ids):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) > 20:
            raise AssertionError("Endlosschleife beim Paging")
        last = ids[(len(calls) - 1) % len(ids)]
        return httpx.Response(200, json={"data": [{"id": last}], "has_more": True, "last_id": last})

    models = providers.list_models("anthropic", "https://api.anthropic.com", KEY, client=make_client(handler))
    assert models == sorted(set(ids))
    assert len(calls) <= len(set(ids)) + 1


def test_openai_content_not_string_is_structure_error():
    handler = lambda r: httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
    with pytest.raises(ProviderError):
        providers.chat("openai", "https://h/v1", KEY, "m", "S", MSGS, client=make_client(handler))
