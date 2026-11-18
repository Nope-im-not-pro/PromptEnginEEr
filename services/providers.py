"""Provider-Adapter fuer OpenAI- und Anthropic-kompatible APIs (Service-Schicht)."""
import httpx

ANTHROPIC_VERSION = "2023-06-01"
MODELS_TIMEOUT = 15.0
CHAT_TIMEOUT = 120.0
MAX_TOKENS = 4096

_STATUS_MESSAGES = {
    401: "API-Key ungueltig oder fehlt (401).",
    403: "API-Key ohne Berechtigung (403).",
    404: "URL oder Modell nicht gefunden (404). Bitte Base-URL und Modell pruefen.",
    429: "Limit erreicht (429). Bitte spaeter erneut versuchen.",
}


class ProviderError(Exception):
    """Fehler beim Provider-Aufruf; user_message ist deutsch und enthaelt nie den API-Key."""

    def __init__(self, user_message: str, status: int | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.status = status


def normalize_base_url(api_type: str, base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    if api_type == "anthropic" and url.endswith("/v1"):
        url = url[:-3].rstrip("/")
    return url


def _headers(api_type: str, api_key: str) -> dict:
    if not api_key.isascii():
        raise ProviderError("API-Key enthaelt ungueltige Zeichen.")
    if api_type == "anthropic":
        return {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION}
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _request(client, method, url, *, headers, timeout, params=None, json=None):
    own = client is None
    if own:
        client = httpx.Client()
    try:
        resp = client.request(method, url, headers=headers, params=params, json=json, timeout=timeout)
    except httpx.TimeoutException:
        raise ProviderError("Zeitueberschreitung: Der Server hat nicht rechtzeitig geantwortet.") from None
    except httpx.ConnectError:
        raise ProviderError("Keine Verbindung zum Server. Bitte Base-URL und Netzwerk pruefen.") from None
    except httpx.HTTPError:
        raise ProviderError("Netzwerkfehler bei der Anfrage an den Server.") from None
    finally:
        if own:
            client.close()
    code = resp.status_code
    if code >= 400:
        if code in _STATUS_MESSAGES:
            msg = _STATUS_MESSAGES[code]
        elif code >= 500:
            msg = f"Server-Fehler beim Provider ({code}). Bitte spaeter erneut versuchen."
        else:
            msg = f"Anfrage abgelehnt ({code})."
        raise ProviderError(msg, code)
    try:
        return resp.json()
    except ValueError:
        raise ProviderError("Unlesbare Antwort vom Server (kein JSON).") from None


def _structure_error() -> ProviderError:
    return ProviderError("Unerwartete Antwort-Struktur vom Server.")


def list_models(api_type: str, base_url: str, api_key: str, *,
                client: httpx.Client | None = None) -> list[str]:
    base = normalize_base_url(api_type, base_url)
    headers = _headers(api_type, api_key)
    ids = set()
    try:
        if api_type == "anthropic":
            params = {"limit": 1000}
            seen_last = set()
            while True:
                data = _request(client, "GET", f"{base}/v1/models", headers=headers,
                                params=params, timeout=MODELS_TIMEOUT)
                ids.update(m["id"] for m in data["data"])
                if not data.get("has_more") or not data.get("last_id") or data["last_id"] in seen_last:
                    break
                seen_last.add(data["last_id"])
                params = {"limit": 1000, "after_id": data["last_id"]}
        else:
            data = _request(client, "GET", f"{base}/models", headers=headers, timeout=MODELS_TIMEOUT)
            ids.update(m["id"] for m in data["data"])
    except (KeyError, TypeError, AttributeError):
        raise _structure_error() from None
    if not all(isinstance(i, str) for i in ids):
        raise _structure_error()
    return sorted(ids)


def chat(api_type: str, base_url: str, api_key: str, model: str,
         system: str, messages: list[dict], *,
         client: httpx.Client | None = None) -> str:
    base = normalize_base_url(api_type, base_url)
    headers = _headers(api_type, api_key)
    try:
        if api_type == "anthropic":
            body = {"model": model, "max_tokens": MAX_TOKENS, "system": system, "messages": messages}
            data = _request(client, "POST", f"{base}/v1/messages", headers=headers,
                            json=body, timeout=CHAT_TIMEOUT)
            text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        else:
            body = {"model": model, "messages": [{"role": "system", "content": system}, *messages]}
            data = _request(client, "POST", f"{base}/chat/completions", headers=headers,
                            json=body, timeout=CHAT_TIMEOUT)
            text = data["choices"][0]["message"]["content"]
    except (KeyError, TypeError, IndexError, AttributeError):
        raise _structure_error() from None
    if not isinstance(text, str):
        raise _structure_error()
    return text
