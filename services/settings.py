"""Provider-Einstellungen aus/in .env (API_TYPE, BASE_URL, API_KEY, MODEL) + THEME + LAYOUT."""
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, set_key

API_TYPES = ("openai", "anthropic")
THEMES = ("system", "light", "dark")
LAYOUTS = ("werkbank", "fokus")
# Plattform-Standard ohne gesetzten LAYOUT-Wert; Plattform kommt explizit vom Einstieg.
DEFAULT_LAYOUT = {"desktop": "werkbank", "android": "fokus"}

_KEYS = {"api_type": "API_TYPE", "base_url": "BASE_URL", "api_key": "API_KEY", "model": "MODEL"}


@dataclass
class Settings:
    api_type: str = "openai"
    base_url: str = ""
    api_key: str = ""
    model: str = ""


def load(path: Path) -> Settings:
    if not path.exists():
        return Settings()
    values = dotenv_values(path, interpolate=False)
    defaults = Settings()
    return Settings(**{f: values.get(k) or getattr(defaults, f) for f, k in _KEYS.items()})


def save(path: Path, s: Settings) -> None:
    path.touch(exist_ok=True)
    for field, key in _KEYS.items():
        set_key(path, key, getattr(s, field), quote_mode="always")


def load_theme(path: Path) -> str:
    if not path.exists():
        return "system"
    theme = dotenv_values(path, interpolate=False).get("THEME")
    return theme if theme in THEMES else "system"


def save_theme(path: Path, theme: str) -> None:
    if theme not in THEMES:
        raise ValueError("Ungueltiger Darstellungsmodus.")
    path.touch(exist_ok=True)
    set_key(path, "THEME", theme, quote_mode="always")


def load_layout(path: Path, platform: str) -> str:
    default = DEFAULT_LAYOUT[platform]
    if not path.exists():
        return default
    layout = dotenv_values(path, interpolate=False).get("LAYOUT")
    return layout if layout in LAYOUTS else default


def save_layout(path: Path, layout: str) -> None:
    if layout not in LAYOUTS:
        raise ValueError("Ungueltiges Layout.")
    path.touch(exist_ok=True)
    set_key(path, "LAYOUT", layout, quote_mode="always")


def validate(s: Settings, require_model: bool = True) -> list[str]:
    errors = []
    if s.api_type not in API_TYPES:
        errors.append("API-Typ muss 'openai' oder 'anthropic' sein.")
    if not s.base_url.startswith(("http://", "https://")):
        errors.append("Basis-URL muss mit http:// oder https:// beginnen.")
    if s.api_type == "anthropic" and not s.api_key:
        errors.append("API-Key fehlt (bei Anthropic Pflicht).")
    if require_model and not s.model:
        errors.append("Modell fehlt.")
    return errors


def is_complete(s: Settings) -> bool:
    return validate(s) == []


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]
