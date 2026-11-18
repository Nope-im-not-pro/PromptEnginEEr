import pytest

from services import paths


@pytest.fixture(autouse=True)
def _isolate_app_dir(request, monkeypatch, tmp_path):
    """Biegt app_dir() auf tmp_path um; echte .env/history.db nie beruehrt."""
    if request.node.get_closest_marker("real_paths"):
        return
    monkeypatch.setattr(paths, "app_dir", lambda: tmp_path)
