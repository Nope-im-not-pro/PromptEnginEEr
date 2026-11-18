import sys
from pathlib import Path

import pytest

from services import paths

real_paths = pytest.mark.real_paths

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FAKE_DIR = Path("C:/fake/PromptEnginEEr").resolve()
FAKE_EXE = FAKE_DIR / "PromptEnginEEr.exe"


@pytest.fixture
def dev(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delattr(paths, "__compiled__", raising=False)


def test_conftest_isolates_app_dir(tmp_path):
    assert paths.app_dir() == tmp_path
    assert paths.env_path() == tmp_path / ".env"
    assert paths.db_path() == tmp_path / "history.db"


@real_paths
def test_dev_mode(dev):
    assert paths.is_frozen() is False
    assert paths.app_dir() == PROJECT_ROOT
    assert paths.resource_dir() == PROJECT_ROOT
    assert paths.env_path() == PROJECT_ROOT / ".env"
    assert paths.db_path() == PROJECT_ROOT / "history.db"


@real_paths
def test_pyinstaller(dev, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(FAKE_EXE))
    monkeypatch.setattr(sys, "_MEIPASS", str(FAKE_DIR / "_internal"), raising=False)
    assert paths.is_frozen() is True
    assert paths.app_dir() == FAKE_DIR
    assert paths.resource_dir() == FAKE_DIR / "_internal"
    assert paths.env_path() == FAKE_DIR / ".env"
    assert paths.db_path() == FAKE_DIR / "history.db"


@real_paths
def test_nuitka(dev, monkeypatch):
    monkeypatch.setattr(paths, "__compiled__", object(), raising=False)
    monkeypatch.setattr(sys, "executable", str(FAKE_EXE))
    assert paths.is_frozen() is True
    assert paths.app_dir() == FAKE_DIR
    assert paths.resource_dir() == FAKE_DIR
    assert paths.env_path() == FAKE_DIR / ".env"
    assert paths.db_path() == FAKE_DIR / "history.db"
