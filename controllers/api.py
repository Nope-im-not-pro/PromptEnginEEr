"""pywebview js_api (Controller): Ablaufsteuerung, jede Methode liefert dict."""
import functools
import webbrowser
from pathlib import Path

import httpx

from models import history
from services import optimizer, providers, settings

NOT_READY = "Bitte zuerst Einstellungen ausfuellen."
THEME_INVALID = "Ungueltiger Darstellungsmodus."
LAYOUT_INVALID = "Ungueltiges Layout."
URL_INVALID = "Link nicht erlaubt."
BROWSER_FAILED = "Browser konnte nicht geoeffnet werden."
# Einziges Ziel fuer den externen Browser (Einstellungen -> Ueber).
REPO_URL = "https://github.com/Nope-im-not-pro/PromptEngineer"


class ApiError(Exception):
    pass


def _endpoint(fn):
    """Wandelt Rueckgabe in {"ok": true, ...} und jede Exception in {"ok": false, "error"}."""
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return {"ok": True, **fn(self, *args, **kwargs)}
        except ApiError as exc:
            return {"ok": False, "error": str(exc)}
        except providers.ProviderError as exc:
            return {"ok": False, "error": exc.user_message}
        except optimizer.ProtocolError:
            return {"ok": False, "error": "Antwort des Modells unbrauchbar. Bitte erneut versuchen."}
        except Exception as exc:  # nie Exception an JS
            return {"ok": False, "error": f"Interner Fehler ({type(exc).__name__})."}
    return wrapper


class Api:
    def __init__(self, env_file: Path, db_file: Path, client: httpx.Client | None = None,
                 platform: str = "desktop"):
        self._env_file = env_file
        self._db_file = db_file
        self._client = client
        self._platform = platform  # "desktop" | "android", explizit vom Einstieg gesetzt

    # --- intern -------------------------------------------------------------

    def _db(self) -> Path:
        history.init_db(self._db_file)
        return self._db_file

    def _resolve(self, data: dict) -> settings.Settings:
        """Settings aus UI-Daten; Key-Regel: gespeicherter Key nur bei gleichem Typ + Host."""
        if not isinstance(data, dict):
            raise ApiError("Ungueltige Eingabe.")
        api_type = str(data.get("api_type") or "")
        base_url = str(data.get("base_url") or "").strip()
        key = str(data.get("api_key") or "").strip()
        if data.get("clear_key"):
            key = ""
        elif not key:
            stored = settings.load(self._env_file)
            same = (stored.api_type == api_type
                    and providers.normalize_base_url(api_type, stored.base_url)
                    == providers.normalize_base_url(api_type, base_url))
            key = stored.api_key if same else ""
        return settings.Settings(api_type=api_type, base_url=base_url, api_key=key,
                                 model=str(data.get("model") or "").strip())

    def _chat_fn(self, s: settings.Settings):
        def chat(system, messages):
            return providers.chat(s.api_type, s.base_url, s.api_key, s.model,
                                  system, messages, client=self._client)
        return chat

    def _ready_settings(self) -> settings.Settings:
        s = settings.load(self._env_file)
        if not settings.is_complete(s):
            raise ApiError(NOT_READY)
        return s

    def _open_session(self, session_id) -> tuple[int, dict]:
        sid = int(session_id)
        item = history.get_session(self._db(), sid)
        if item is None:
            raise ApiError("Sitzung nicht gefunden.")
        if item["status"] == "done":
            raise ApiError("Sitzung bereits abgeschlossen.")
        return sid, item

    def _step(self, s, sid: int | None, raw_prompt: str, turns: list[dict],
              message: dict, require_clear: bool = False) -> dict:
        result, text = optimizer.run_step(self._chat_fn(s), turns + [message],
                                          require_clear=require_clear)
        db = self._db()
        if sid is None:
            sid = history.create_session(db, raw_prompt, s.api_type, s.model)
        history.add_turn(db, sid, "user", message["content"])
        history.add_turn(db, sid, "assistant", text)
        if result["status"] == "clear":
            history.finish_session(db, sid, result["optimized_prompt"])
        return {"session_id": sid, "result": result}

    # --- Einstellungen ------------------------------------------------------

    @_endpoint
    def get_settings(self):
        s = settings.load(self._env_file)
        return {
            "settings": {"api_type": s.api_type, "base_url": s.base_url, "model": s.model,
                         "has_key": bool(s.api_key), "key_hint": settings.mask_key(s.api_key)},
            "complete": settings.is_complete(s),
            "theme": settings.load_theme(self._env_file),
            "layout": settings.load_layout(self._env_file, self._platform),
        }

    @_endpoint
    def set_theme(self, theme):
        if not isinstance(theme, str) or theme not in settings.THEMES:
            raise ApiError(THEME_INVALID)
        settings.save_theme(self._env_file, theme)
        return {}

    @_endpoint
    def set_layout(self, layout):
        if not isinstance(layout, str) or layout not in settings.LAYOUTS:
            raise ApiError(LAYOUT_INVALID)
        settings.save_layout(self._env_file, layout)
        return {}

    @_endpoint
    def open_url(self, url):
        """Desktop: Repo-Link im System-Browser; jede andere URL abgelehnt."""
        if url != REPO_URL:
            raise ApiError(URL_INVALID)
        if not webbrowser.open(REPO_URL):
            raise ApiError(BROWSER_FAILED)
        return {}

    @_endpoint
    def save_settings(self, data):
        s = self._resolve(data)
        errors = settings.validate(s)
        if errors:
            raise ApiError(" ".join(errors))
        settings.save(self._env_file, s)
        return {}

    @_endpoint
    def list_models(self, data):
        s = self._resolve(data)
        errors = settings.validate(s, require_model=False)
        if errors:
            raise ApiError(" ".join(errors))
        return {"models": providers.list_models(s.api_type, s.base_url, s.api_key,
                                                client=self._client)}

    # --- Optimieren ---------------------------------------------------------

    @_endpoint
    def optimize_start(self, raw_prompt):
        s = self._ready_settings()
        raw = str(raw_prompt or "").strip()
        if not raw:
            raise ApiError("Bitte einen Prompt eingeben.")
        return self._step(s, None, raw, [], optimizer.start_message(raw))

    @_endpoint
    def optimize_choose(self, session_id, index):
        s = self._ready_settings()
        sid, item = self._open_session(session_id)
        last = [t for t in item["turns"] if t["role"] == "assistant"]
        options = optimizer.parse_response(last[-1]["content"]).get("options", []) if last else []
        if type(index) is not int or not 0 <= index < len(options):
            raise ApiError("Ungueltige Auswahl.")
        out = self._step(s, sid, item["raw_prompt"], item["turns"],
                         optimizer.choice_message(options[index]), require_clear=True)
        return {"result": out["result"]}

    @_endpoint
    def optimize_refine(self, session_id, prompt):
        s = self._ready_settings()
        text = str(prompt or "").strip()
        if not text:
            raise ApiError("Bitte einen Prompt eingeben.")
        sid, item = self._open_session(session_id)
        out = self._step(s, sid, item["raw_prompt"], item["turns"],
                         optimizer.refine_message(text))
        return {"result": out["result"]}

    # --- Historie -----------------------------------------------------------

    @_endpoint
    def history_list(self):
        return {"items": history.list_sessions(self._db())}

    @_endpoint
    def history_get(self, session_id):
        item = history.get_session(self._db(), int(session_id))
        if item is None:
            raise ApiError("Eintrag nicht gefunden.")
        return {"item": item}

    @_endpoint
    def history_delete(self, session_id):
        if not history.delete_session(self._db(), int(session_id)):
            raise ApiError("Eintrag nicht gefunden.")
        return {}
