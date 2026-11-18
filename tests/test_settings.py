import pytest

from services import settings
from services.settings import Settings


def test_load_missing_file_gives_defaults(tmp_path):
    assert settings.load(tmp_path / ".env") == Settings()


def test_load_existing_values(tmp_path):
    p = tmp_path / ".env"
    p.write_text("API_TYPE=anthropic\nBASE_URL=https://api.anthropic.com\n"
                 "API_KEY=sk-1\nMODEL=m1\n", encoding="utf-8")
    assert settings.load(p) == Settings("anthropic", "https://api.anthropic.com", "sk-1", "m1")


def test_save_creates_file_and_roundtrip(tmp_path):
    p = tmp_path / ".env"
    s = Settings("openai", "http://localhost:11434/v1", "sk-x", "llama3")
    settings.save(p, s)
    assert p.exists()
    assert settings.load(p) == s


@pytest.mark.parametrize("key", [
    "a#b", "a=b", "a b", 'a"b', "a'b", " #=\"' mixed ' \" = # ",
])
def test_save_key_special_chars_roundtrip(tmp_path, key):
    p = tmp_path / ".env"
    s = Settings("anthropic", "https://api.anthropic.com", key, "m")
    settings.save(p, s)
    assert settings.load(p) == s
    settings.save(p, s)
    assert settings.load(p) == s


@pytest.mark.parametrize("quoted", [False, True])
def test_load_no_variable_interpolation(tmp_path, monkeypatch, quoted):
    monkeypatch.setenv("PE_TEST_VAR", "leak")
    p = tmp_path / ".env"
    v = '"sk-${PE_TEST_VAR}-${FOO}"' if quoted else "sk-${PE_TEST_VAR}-${FOO}"
    p.write_text(f"FOO=bar\nAPI_KEY={v}\n", encoding="utf-8")
    assert settings.load(p).api_key == "sk-${PE_TEST_VAR}-${FOO}"


def test_save_key_with_dollar_brace_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("PE_TEST_VAR", "leak")
    p = tmp_path / ".env"
    s = Settings("anthropic", "https://api.anthropic.com", "a${PE_TEST_VAR}b", "m")
    settings.save(p, s)
    assert settings.load(p) == s


def test_save_keeps_foreign_keys(tmp_path):
    p = tmp_path / ".env"
    p.write_text("FOO=bar\nAPI_KEY=old\n", encoding="utf-8")
    settings.save(p, Settings("openai", "https://api.openai.com/v1", "new", "gpt"))
    from dotenv import dotenv_values
    values = dotenv_values(p)
    assert values["FOO"] == "bar"
    assert settings.load(p).api_key == "new"


def test_validate_ok_and_openai_without_key():
    assert settings.validate(Settings("openai", "http://localhost:11434/v1", "", "m")) == []
    assert settings.is_complete(Settings("openai", "https://x/v1", "", "m"))


def test_validate_errors_each_one_message():
    assert len(settings.validate(Settings("foo", "https://x", "k", "m"))) == 1
    assert len(settings.validate(Settings("openai", "ftp://x", "k", "m"))) == 1
    assert len(settings.validate(Settings("openai", "", "k", "m"))) == 1
    assert len(settings.validate(Settings("anthropic", "https://x", "", "m"))) == 1
    assert len(settings.validate(Settings("openai", "https://x", "k", ""))) == 1
    assert settings.validate(Settings("openai", "https://x", "k", ""), require_model=False) == []
    errs = settings.validate(Settings("foo", "x", "", ""))
    assert len(errs) == 3
    assert all(isinstance(e, str) and e for e in errs)
    assert not settings.is_complete(Settings())


def test_mask_key():
    assert settings.mask_key("") == ""
    assert settings.mask_key("abc") == "****"
    assert settings.mask_key("abcd") == "****"
    assert settings.mask_key("sk-abcdef1234") == "****1234"


# --- Theme ------------------------------------------------------------------

def test_load_theme_missing_file_creates_nothing(tmp_path):
    p = tmp_path / ".env"
    assert settings.load_theme(p) == "system"
    assert not p.exists()


def test_load_theme_missing_key(tmp_path):
    p = tmp_path / ".env"
    p.write_text("API_TYPE=openai\nFOO=bar\n", encoding="utf-8")
    assert settings.load_theme(p) == "system"


@pytest.mark.parametrize("value", ["blau", '""', "DARK"])
def test_load_theme_invalid_value(tmp_path, value):
    p = tmp_path / ".env"
    p.write_text(f"THEME={value}\n", encoding="utf-8")
    assert settings.load_theme(p) == "system"


@pytest.mark.parametrize("theme", settings.THEMES)
def test_save_theme_creates_file_and_roundtrip(tmp_path, theme):
    p = tmp_path / ".env"
    settings.save_theme(p, theme)
    assert p.exists()
    assert settings.load_theme(p) == theme


@pytest.mark.parametrize("theme", ["blau", "", None, 1])
def test_save_theme_invalid_raises_file_unchanged(tmp_path, theme):
    p = tmp_path / ".env"
    with pytest.raises(ValueError):
        settings.save_theme(p, theme)
    assert not p.exists()
    p.write_text("THEME=\"dark\"\nFOO=bar\n", encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        settings.save_theme(p, theme)
    assert p.read_text(encoding="utf-8") == before


def test_save_theme_keeps_provider_and_foreign_keys(tmp_path):
    p = tmp_path / ".env"
    s = Settings("anthropic", "https://api.anthropic.com", "sk-1", "m1")
    settings.save(p, s)
    with open(p, "a", encoding="utf-8") as f:
        f.write("FOO=bar\n")
    settings.save_theme(p, "dark")
    settings.save_theme(p, "light")
    from dotenv import dotenv_values
    assert dotenv_values(p)["FOO"] == "bar"
    assert settings.load(p) == s
    assert settings.load_theme(p) == "light"


def test_save_settings_keeps_theme(tmp_path):
    p = tmp_path / ".env"
    settings.save_theme(p, "dark")
    settings.save(p, Settings("openai", "https://x/v1", "k", "m"))
    assert settings.load_theme(p) == "dark"
    assert settings.is_complete(settings.load(p))


def test_no_forbidden_imports():
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(settings))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert not names & {"controllers", "models", "webview"}


# --- Layout -----------------------------------------------------------------

@pytest.mark.parametrize("platform,expected", [("desktop", "werkbank"), ("android", "fokus")])
def test_load_layout_missing_file_platform_default(tmp_path, platform, expected):
    p = tmp_path / ".env"
    assert settings.load_layout(p, platform) == expected
    assert not p.exists()


@pytest.mark.parametrize("platform,expected", [("desktop", "werkbank"), ("android", "fokus")])
def test_load_layout_missing_key_platform_default(tmp_path, platform, expected):
    p = tmp_path / ".env"
    p.write_text("THEME=dark\nFOO=bar\n", encoding="utf-8")
    assert settings.load_layout(p, platform) == expected


@pytest.mark.parametrize("value", ["werkbank", "fokus"])
@pytest.mark.parametrize("platform", ["desktop", "android"])
def test_load_layout_existing_value(tmp_path, value, platform):
    p = tmp_path / ".env"
    p.write_text(f'LAYOUT="{value}"\n', encoding="utf-8")
    assert settings.load_layout(p, platform) == value


@pytest.mark.parametrize("value", ["kachel", '""', "FOKUS"])
def test_load_layout_invalid_value_platform_default(tmp_path, value):
    p = tmp_path / ".env"
    p.write_text(f"LAYOUT={value}\n", encoding="utf-8")
    assert settings.load_layout(p, "desktop") == "werkbank"
    assert settings.load_layout(p, "android") == "fokus"


def test_load_layout_unknown_platform_raises(tmp_path):
    with pytest.raises(KeyError):
        settings.load_layout(tmp_path / ".env", "ios")


@pytest.mark.parametrize("layout", settings.LAYOUTS)
def test_save_layout_creates_file_and_roundtrip(tmp_path, layout):
    p = tmp_path / ".env"
    settings.save_layout(p, layout)
    assert p.exists()
    assert settings.load_layout(p, "desktop") == layout
    assert settings.load_layout(p, "android") == layout


@pytest.mark.parametrize("layout", ["kachel", "", None, 1, "Werkbank"])
def test_save_layout_invalid_raises_file_unchanged(tmp_path, layout):
    p = tmp_path / ".env"
    with pytest.raises(ValueError):
        settings.save_layout(p, layout)
    assert not p.exists()
    p.write_text("LAYOUT=\"fokus\"\nFOO=bar\n", encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        settings.save_layout(p, layout)
    assert p.read_text(encoding="utf-8") == before


def test_save_layout_keeps_provider_theme_and_foreign_keys(tmp_path):
    p = tmp_path / ".env"
    s = Settings("anthropic", "https://api.anthropic.com", "sk-1", "m1")
    settings.save(p, s)
    settings.save_theme(p, "dark")
    with open(p, "a", encoding="utf-8") as f:
        f.write("FOO=bar\n")
    settings.save_layout(p, "fokus")
    settings.save_layout(p, "werkbank")
    from dotenv import dotenv_values
    assert dotenv_values(p)["FOO"] == "bar"
    assert settings.load(p) == s
    assert settings.load_theme(p) == "dark"
    assert settings.load_layout(p, "android") == "werkbank"
