"""Laufzeit-Pfade fuer Dev-Modus, PyInstaller (--onedir) und Nuitka (--standalone)."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    # Nuitka setzt __compiled__ als Modul-Global in kompilierten Modulen.
    return bool(getattr(sys, "frozen", False)) or "__compiled__" in globals()


def app_dir() -> Path:
    """Beschreibbarer App-Ordner: exe-Ordner (frozen) oder Projekt-Root."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return _PROJECT_ROOT


def resource_dir() -> Path:
    """Ordner, der static/ enthaelt."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass).resolve()
    if is_frozen():
        return app_dir()
    return _PROJECT_ROOT


def env_path() -> Path:
    return app_dir() / ".env"


def db_path() -> Path:
    return app_dir() / "history.db"
