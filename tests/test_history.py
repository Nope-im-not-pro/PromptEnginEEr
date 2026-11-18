import inspect
import re

from models import history


def _db(tmp_path):
    p = tmp_path / "history.db"
    history.init_db(p)
    return p


def test_init_db_idempotent(tmp_path):
    p = tmp_path / "history.db"
    history.init_db(p)
    history.init_db(p)
    assert p.exists()


def test_create_session_and_turns_in_order(tmp_path):
    p = _db(tmp_path)
    sid = history.create_session(p, "roh", "openai", "gpt-x")
    assert isinstance(sid, int)
    history.add_turn(p, sid, "user", "a")
    history.add_turn(p, sid, "assistant", "b")
    history.add_turn(p, sid, "user", "c")
    assert history.get_turns(p, sid) == [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]


def test_new_session_is_open(tmp_path):
    p = _db(tmp_path)
    sid = history.create_session(p, "roh", "openai", "m")
    s = history.get_session(p, sid)
    assert s["status"] == "open"
    assert s["optimized_prompt"] is None
    assert s["turns"] == []


def test_finish_session(tmp_path):
    p = _db(tmp_path)
    sid = history.create_session(p, "roh", "anthropic", "claude")
    before = history.get_session(p, sid)["updated_at"]
    history.finish_session(p, sid, "fertig")
    s = history.get_session(p, sid)
    assert s["status"] == "done"
    assert s["optimized_prompt"] == "fertig"
    assert s["updated_at"] >= before
    assert s["updated_at"].endswith("+00:00")


def test_list_sessions_newest_first_and_limit(tmp_path):
    p = _db(tmp_path)
    ids = [history.create_session(p, f"p{i}", "openai", "m") for i in range(3)]
    items = history.list_sessions(p)
    assert [i["id"] for i in items] == list(reversed(ids))
    assert set(items[0]) == {"id", "created_at", "updated_at", "status",
                             "raw_prompt", "model"}
    assert [i["id"] for i in history.list_sessions(p, limit=2)] == [ids[2], ids[1]]


def test_get_session_unknown(tmp_path):
    p = _db(tmp_path)
    assert history.get_session(p, 999) is None


def test_delete_session_cascades(tmp_path):
    p = _db(tmp_path)
    sid = history.create_session(p, "roh", "openai", "m")
    history.add_turn(p, sid, "user", "x")
    assert history.delete_session(p, sid) is True
    assert history.get_session(p, sid) is None
    assert history.get_turns(p, sid) == []
    assert history.delete_session(p, sid) is False


def test_unicode_roundtrip(tmp_path):
    p = _db(tmp_path)
    text = "Grüße äöüß 🚀\nZeile 2\r\nZeile 3"
    sid = history.create_session(p, text, "openai", "m")
    history.add_turn(p, sid, "user", text)
    history.finish_session(p, sid, text)
    s = history.get_session(p, sid)
    assert s["raw_prompt"] == text
    assert s["optimized_prompt"] == text
    assert s["turns"] == [{"role": "user", "content": text}]
    assert history.list_sessions(p)[0]["raw_prompt"] == text


def test_sql_only_parameterized():
    src = inspect.getsource(history)
    assert not re.search(r"""f["'].*(SELECT|INSERT|UPDATE|DELETE)""", src, re.I)
    assert not re.search(r"""(SELECT|INSERT|UPDATE|DELETE)[^\n]*["']\s*%""", src, re.I)
    assert ".format(" not in src
