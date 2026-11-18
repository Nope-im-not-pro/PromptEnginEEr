import json

import pytest

from services import optimizer
from services.optimizer import ProtocolError, parse_response, run_step

CLEAR = '{"status": "clear", "optimized_prompt": "Du bist ..."}'
UNCLEAR = json.dumps({
    "status": "unclear",
    "question": "Was soll entstehen?",
    "options": [{"label": "Text", "description": "Fliesstext"}, {"label": "Code"}],
})


class FakeChat:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, system, messages):
        self.calls.append((system, [dict(m) for m in messages]))
        return self.answers.pop(0)


# --- SYSTEM_PROMPT / Nachrichten -------------------------------------------

def test_system_prompt_covers_rules():
    sp = optimizer.SYSTEM_PROMPT.lower()
    for word in ("absicht", "genau eine", "2-5", "json", "sprache",
                 "rolle", "kontext", "ausgabeformat", "platzhalter",
                 "unclear", "clear", "optimized_prompt", "erfinde"):
        assert word in sp, word


def test_start_and_refine_message():
    assert optimizer.start_message("mach was") == {"role": "user", "content": "mach was"}
    m = optimizer.refine_message("neu")
    assert m["role"] == "user" and "neu" in m["content"]


def test_choice_message_contains_label_description_and_clear_instruction():
    m = optimizer.choice_message({"label": "Code", "description": "Python-Skript"})
    assert m["role"] == "user"
    assert "Code" in m["content"] and "Python-Skript" in m["content"]
    assert '"clear"' in m["content"]


# --- parse_response ---------------------------------------------------------

def test_parse_plain_json():
    assert parse_response(CLEAR) == {"status": "clear", "optimized_prompt": "Du bist ..."}


def test_parse_fenced_json():
    r = parse_response("```json\n" + UNCLEAR + "\n```")
    assert r["status"] == "unclear"
    assert r["options"][1] == {"label": "Code", "description": ""}


def test_parse_with_surrounding_text():
    assert parse_response("Hier:\n" + CLEAR + "\nFertig.")["status"] == "clear"


FENCED_PROMPT = "Beispiel:\n```python\nprint(1)\n```\nEnde"


@pytest.mark.parametrize("wrap", [lambda s: s, lambda s: "```json\n" + s + "\n```"])
def test_parse_keeps_fences_inside_optimized_prompt(wrap):
    text = wrap(json.dumps({"status": "clear", "optimized_prompt": FENCED_PROMPT}))
    assert parse_response(text)["optimized_prompt"] == FENCED_PROMPT


@pytest.mark.parametrize("text", [
    "kein json",
    "{kaputt}",
    '{"status": "maybe"}',
    '{"status": "clear", "optimized_prompt": "  "}',
    '{"status": "clear"}',
    '{"status": "unclear", "options": [{"label": "a"}, {"label": "b"}]}',
    '{"status": "unclear", "question": "q", "options": [{"label": "a"}]}',
    '{"status": "unclear", "question": "q", "options": '
    + json.dumps([{"label": str(i)} for i in range(6)]) + "}",
    '{"status": "unclear", "question": "q", "options": [{"label": "a"}, {"label": ""}]}',
    '[1, 2]',
])
def test_parse_rejects_invalid(text):
    with pytest.raises(ProtocolError):
        parse_response(text)


# --- run_step ---------------------------------------------------------------

def test_run_step_valid_single_call():
    chat = FakeChat(CLEAR)
    msgs = [optimizer.start_message("x")]
    result, raw = run_step(chat, msgs)
    assert result["status"] == "clear" and raw == CLEAR
    assert len(chat.calls) == 1
    assert chat.calls[0][0] == optimizer.SYSTEM_PROMPT
    assert msgs == [optimizer.start_message("x")]


def test_run_step_repairs_once():
    chat = FakeChat("Unsinn", UNCLEAR)
    msgs = [optimizer.start_message("x")]
    result, raw = run_step(chat, msgs)
    assert result["status"] == "unclear" and raw == UNCLEAR
    assert len(chat.calls) == 2
    second = chat.calls[1][1]
    assert second[-2] == {"role": "assistant", "content": "Unsinn"}
    assert second[-1]["role"] == "user" and "JSON" in second[-1]["content"]
    assert msgs == [optimizer.start_message("x")]


def test_run_step_twice_invalid_raises():
    chat = FakeChat("a", "b")
    with pytest.raises(ProtocolError):
        run_step(chat, [optimizer.start_message("x")])
    assert len(chat.calls) == 2


def test_run_step_require_clear_retry_success():
    chat = FakeChat(UNCLEAR, CLEAR)
    result, raw = run_step(chat, [optimizer.start_message("x")], require_clear=True)
    assert result["status"] == "clear" and raw == CLEAR
    assert len(chat.calls) == 2
    assert '"clear"' in chat.calls[1][1][-1]["content"]


def test_run_step_require_clear_twice_unclear_raises():
    chat = FakeChat(UNCLEAR, UNCLEAR)
    with pytest.raises(ProtocolError):
        run_step(chat, [optimizer.start_message("x")], require_clear=True)


def test_no_forbidden_imports():
    src = open(optimizer.__file__, encoding="utf-8").read()
    for mod in ("providers", "controllers", "models"):
        assert f"import {mod}" not in src and f"from {mod}" not in src
        assert f"services.{mod}" not in src
